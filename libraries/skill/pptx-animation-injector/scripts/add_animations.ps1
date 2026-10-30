param(
  [Parameter(Mandatory=$true)][string]$PptxPath,
  [Parameter(Mandatory=$false)][string]$ManifestPath,
  [switch]$ExportPreviews
)

$ErrorActionPreference = 'Stop'

# ---- msoAnimEffect 枚举（PowerPoint 固定值）----
$effectMap = [ordered]@{
  'fade'      = 10   # msoAnimEffectFade
  'fly'       = 2    # msoAnimEffectFly
  'wipe'      = 13   # msoAnimEffectWipe
  'zoom'      = 19   # msoAnimEffectZoom
  'appear'    = 1    # msoAnimEffectAppear
  'peek'      = 12   # msoAnimEffectPeek
  'rise'      = 12
  'dissolve'  = 9    # msoAnimEffectDissolve
}

# ---- msoAnimTriggerType 枚举：1=onclick, 2=withPrev, 3=afterPrev ----
function TriggerId($t){
  switch ([string]$t) {
    'onclick'     { return 1 }
    'click'       { return 1 }
    'withEffect'  { return 2 }
    'withPrev'    { return 2 }
    'afterEffect' { return 3 }
    'afterPrev'   { return 3 }
    default       { return 1 }
  }
}

$ppt = New-Object -ComObject PowerPoint.Application
# 注意：本机禁止 Visible=0，必须 -1，否则抛 "Hiding the application window is not allowed"
$ppt.Visible = -1

try {
  if ($ManifestPath -and (Test-Path $ManifestPath)) {
    $raw = Get-Content $ManifestPath -Encoding UTF8 | ConvertFrom-Json
    $manifest = $raw
  } else {
    $manifest = $null
  }

  $pres = $ppt.Presentations.Open($PptxPath)

  if ($manifest) {
    $total = 0
    foreach ($key in $manifest.PSObject.Properties.Name) {
      $idx = [int]$key
      try { $slide = $pres.Slides.Item($idx) } catch { Write-Host ("slide {0} missing, skip" -f $idx); continue }
      $seq = $slide.TimeLine.MainSequence
      $effects = $manifest.$key
      Write-Host ("slide {0}: {1} effects" -f $idx, $effects.Count)
      foreach ($e in $effects) {
        $spid  = [int]$e.spid
        $preset = [string]$e.preset
        if (-not $effectMap.Contains($preset)) { $preset = 'fade' }
        $et  = $effectMap[$preset]
        $trg = TriggerId([string]$e.trig)
        $shape = $null
        foreach ($sh in $slide.Shapes) {
          if ($sh.Id -eq $spid) { $shape = $sh; break }
        }
        if ($null -eq $shape) { Write-Host ("  spid {0} not found, skip" -f $spid); continue }
        try {
          $seq.AddEffect($shape, $et, 0, $trg) | Out-Null
          $total++
        } catch {
          Write-Host ("  effect failed spid {0}: {1}" -f $spid, $_.Exception.Message)
        }
      }
    }
    $pres.Save()
    Write-Host ("SAVED with {0} animations" -f $total)
  } else {
    Write-Host "no manifest provided; save only"
    $pres.Save()
  }

  if ($ExportPreviews) {
    Write-Host "WARN: Slide.Export 在无头环境可能卡死，仅在可见桌面会话使用。"
    $dir = Join-Path (Split-Path $PptxPath) "ppt_preview"
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    for ($i = 1; $i -le $pres.Slides.Count; $i++) {
      $out = Join-Path $dir ("slide{0:D2}.png" -f $i)
      $pres.Slides.Item($i).Export($out, "PNG", 1600, 900)
      Write-Host ("exported {0}" -f $out)
    }
  }

  $pres.Close()
} catch {
  Write-Host ("ERR: {0}" -f $_.Exception.Message)
  try { $pres.Close() } catch {}
} finally {
  $ppt.Quit()
}
