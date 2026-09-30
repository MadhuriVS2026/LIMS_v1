/**
 * TanStack Query hooks for worksheets, plus the live-recalculation hook.
 */
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { worksheetApi } from '../api/worksheetApi';
import type {
  CreateWorksheetRequest,
  SaveWorksheetRequest,
  WorksheetComputed,
  WorksheetValuesRequest,
} from '../models/testTemplate.types';

export function useWorksheetForLine(lineId: number | undefined) {
  return useQuery({
    queryKey: ['worksheet-for-line', lineId],
    queryFn: () => worksheetApi.getForLine(lineId as number),
    enabled: lineId != null,
  });
}

export function useWorksheet(worksheetId: number | undefined) {
  return useQuery({
    queryKey: ['worksheet', worksheetId],
    queryFn: () => worksheetApi.get(worksheetId as number),
    enabled: worksheetId != null,
  });
}

export function useWorksheetsForTrf(trfId: number | undefined) {
  return useQuery({
    queryKey: ['worksheets-for-trf', trfId],
    queryFn: () => worksheetApi.listForTrf(trfId as number),
    enabled: trfId != null,
  });
}

function useWorksheetInvalidation() {
  const qc = useQueryClient();
  return (worksheetId?: number, lineId?: number, trfId?: number) => {
    if (worksheetId != null) qc.invalidateQueries({ queryKey: ['worksheet', worksheetId] });
    if (lineId != null) qc.invalidateQueries({ queryKey: ['worksheet-for-line', lineId] });
    if (trfId != null) {
      qc.invalidateQueries({ queryKey: ['worksheets-for-trf', trfId] });
      //  A confirmed result lands on the test line, so the TRF's own projection
      //  is stale too.
      qc.invalidateQueries({ queryKey: ['trf-detail', trfId] });
    }
  };
}

export function useCreateWorksheet() {
  const invalidate = useWorksheetInvalidation();
  return useMutation({
    mutationFn: ({ lineId, payload }: { lineId: number; payload: CreateWorksheetRequest; trfId?: number }) =>
      worksheetApi.createForLine(lineId, payload),
    onSuccess: (data, variables) =>
      invalidate(data.worksheet.id, variables.lineId, variables.trfId),
  });
}

export function useSaveWorksheetValues() {
  const invalidate = useWorksheetInvalidation();
  return useMutation({
    mutationFn: ({
      worksheetId,
      payload,
    }: {
      worksheetId: number;
      payload: SaveWorksheetRequest;
      lineId?: number;
      trfId?: number;
    }) => worksheetApi.saveValues(worksheetId, payload),
    onSuccess: (_data, variables) =>
      invalidate(variables.worksheetId, variables.lineId, variables.trfId),
  });
}

export function useConfirmWorksheet() {
  const invalidate = useWorksheetInvalidation();
  return useMutation({
    mutationFn: ({ worksheetId }: { worksheetId: number; lineId?: number; trfId?: number }) =>
      worksheetApi.confirm(worksheetId),
    onSuccess: (_data, variables) =>
      invalidate(variables.worksheetId, variables.lineId, variables.trfId),
  });
}

export function useSubmitForReview() {
  const invalidate = useWorksheetInvalidation();
  return useMutation({
    mutationFn: ({
      worksheetId,
      comments,
    }: {
      worksheetId: number;
      comments?: string;
      lineId?: number;
      trfId?: number;
    }) => worksheetApi.submitForReview(worksheetId, comments),
    onSuccess: (_data, variables) =>
      invalidate(variables.worksheetId, variables.lineId, variables.trfId),
  });
}

export function useReferBackWorksheet() {
  const invalidate = useWorksheetInvalidation();
  return useMutation({
    mutationFn: ({
      worksheetId,
      comments,
    }: {
      worksheetId: number;
      comments: string;
      lineId?: number;
      trfId?: number;
    }) => worksheetApi.referBack(worksheetId, comments),
    onSuccess: (_data, variables) =>
      invalidate(variables.worksheetId, variables.lineId, variables.trfId),
  });
}

export function useApproveWorksheetReview() {
  const invalidate = useWorksheetInvalidation();
  return useMutation({
    mutationFn: ({
      worksheetId,
      comments,
    }: {
      worksheetId: number;
      comments?: string;
      lineId?: number;
      trfId?: number;
    }) => worksheetApi.approveReview(worksheetId, comments),
    onSuccess: (_data, variables) =>
      invalidate(variables.worksheetId, variables.lineId, variables.trfId),
  });
}

/**
 * Debounced live recalculation.
 *
 * Deliberately not a `useQuery`: the values being previewed are transient form
 * state, so caching them by key would fill the query cache with entries that
 * are stale the moment the next keystroke lands. This keeps one in-flight
 * request and one result.
 *
 * `stale` lets the form dim the computed columns while a recalculation is
 * pending, so an analyst is never looking at a number that no longer
 * corresponds to what is on screen.
 */
export function usePreview(worksheetId: number | undefined, delayMs = 400) {
  const [computed, setComputed] = useState<WorksheetComputed | null>(null);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  //  Monotonic token: an earlier request that resolves late must not overwrite a
  //  later one's result.
  const latest = useRef(0);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  function request(payload: WorksheetValuesRequest, immediate = false) {
    if (worksheetId == null) return;
    if (timer.current) clearTimeout(timer.current);
    setStale(true);

    const run = async () => {
      const token = ++latest.current;
      try {
        const result = await worksheetApi.preview(worksheetId, payload);
        if (token !== latest.current) return;
        setComputed(result);
        setError(null);
      } catch (err) {
        if (token !== latest.current) return;
        setError(err);
      } finally {
        if (token === latest.current) setStale(false);
      }
    };

    if (immediate) void run();
    else timer.current = setTimeout(() => void run(), delayMs);
  }

  function reset(next: WorksheetComputed | null) {
    if (timer.current) clearTimeout(timer.current);
    latest.current += 1;
    setComputed(next);
    setStale(false);
    setError(null);
  }

  return { computed, stale, error, request, reset };
}
