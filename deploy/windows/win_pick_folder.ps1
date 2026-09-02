param(
    [string]$Title = "Seleziona cartella pratica"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$selectedPath = $null
$owner = New-Object System.Windows.Forms.Form
$owner.Text = "Securtek"
$owner.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$owner.ShowInTaskbar = $false
$owner.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$owner.Size = New-Object System.Drawing.Size(1, 1)
$owner.Opacity = 0
$owner.TopMost = $true
$owner.Add_Shown({
    try {
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = $Title
        $dialog.ShowNewFolderButton = $true
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            $script:selectedPath = $dialog.SelectedPath
        }
    }
    finally {
        $owner.Close()
    }
})

[void]$owner.ShowDialog()

if ($selectedPath) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $selectedPath
}
