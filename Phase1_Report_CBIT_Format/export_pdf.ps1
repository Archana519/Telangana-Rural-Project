param([string]$Docx, [string]$Pdf)
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$d = $w.Documents.Open($Docx)
$d.Repaginate()
$d.ExportAsFixedFormat($Pdf, 17)
$d.Close(0)
$w.Quit()
