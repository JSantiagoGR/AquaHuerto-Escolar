param([string]$docx)
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$d = $w.Documents.Open($docx)
$d.Fields.Update() | Out-Null
foreach ($t in $d.TablesOfContents) { $t.Update() }
$d.Save()
$pdf = [System.IO.Path]::ChangeExtension($docx, ".pdf")
$d.ExportAsFixedFormat($pdf, 17)
$d.Close()
$w.Quit()
Write-Output "PDF: $pdf"
