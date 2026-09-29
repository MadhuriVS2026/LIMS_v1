# Analysis-only helper: xlrd cannot read formulas from legacy .xls files.
# Drive Excel via COM (read-only) to dump R1C1-free A1-style formulas for the .xls forms.
param(
    [string]$FormsDir = "d:\Anti Gravity LIMS\rd-lab-instance\Test types",
    [string]$Out = "d:\Anti Gravity LIMS\rd-lab-instance\_inspect_tests\xls_formulas_dump.txt",
    [int]$MaxRow = 140,
    [int]$MaxCol = 22
)

$ErrorActionPreference = "Stop"
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$sb = New-Object System.Text.StringBuilder

try {
    Get-ChildItem -Path $FormsDir -Filter *.xls | Sort-Object Name | ForEach-Object {
        $f = $_
        [void]$sb.AppendLine("")
        [void]$sb.AppendLine(("=" * 90))
        [void]$sb.AppendLine("FILE: $($f.Name)")
        [void]$sb.AppendLine(("=" * 90))
        $wb = $excel.Workbooks.Open($f.FullName, 0, $true)
        try {
            foreach ($ws in $wb.Worksheets) {
                $used = $ws.UsedRange
                $rows = [Math]::Min($used.Rows.Count + $used.Row - 1, $MaxRow)
                $cols = [Math]::Min($used.Columns.Count + $used.Column - 1, $MaxCol)
                [void]$sb.AppendLine("  --- sheet: $($ws.Name) (usedRows=$($used.Rows.Count), usedCols=$($used.Columns.Count)) ---")
                for ($r = 1; $r -le $rows; $r++) {
                    $line = @()
                    for ($c = 1; $c -le $cols; $c++) {
                        $cell = $ws.Cells.Item($r, $c)
                        $fx = $cell.Formula
                        if ($null -eq $fx -or "$fx" -eq "") { continue }
                        $addr = $cell.Address(0, 0)
                        if ($cell.HasFormula) {
                            $line += "$addr[F]=$fx"
                        }
                        else {
                            $line += "$addr[V]=$fx"
                        }
                    }
                    if ($line.Count -gt 0) {
                        [void]$sb.AppendLine("    " + ($line -join " | "))
                    }
                }
            }
        }
        finally {
            $wb.Close($false)
        }
    }
}
finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}

Set-Content -Path $Out -Value $sb.ToString() -Encoding UTF8
Write-Output "Wrote $Out"
