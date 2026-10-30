# Background watch Git console suppression

Base: `5f70d78bd39288e27eb3e674d815d3130cb51f4f`.

Three natural observations at 07:10–07:12 UTC associated each brief visible
Terminal window with `git -C <Source> rev-parse HEAD`, parented by the existing
workbench watch process. Observed spacing was about 62 seconds; the scan keeps
its existing 60-second sleep after work. This is distinct from task restarts
or a model wake. OS event subscription was denied and was not retried.

The periodic `workbench_refresh.scan_dirty` Git subprocess now passes Windows
`CREATE_NO_WINDOW`; non-Windows passes zero. Arguments, capture of stdout and
stderr, text decoding, ten-second timeout, check=False, fallback and scan logic
are unchanged. No task/service/global console setting is changed.

Validation: the existing Markdown workbench file plus a real scan-path assertion
for Windows/non-Windows flags passed 23 tests. Test confirms the same Git argv,
capture flags, timeout and scan result. No production watch was reloaded by the
author. Original S029 review, S010 acceptance, Rooter installation and one
natural post-install observation are still required: no flash and continuing
normal business scan. Candidate presence does not prove adoption or resolved
production symptoms. Keep any artificial invocation separate from natural
observation.

This independent two-code-file slice contains no receiver implementation and
does not depend on the frozen comparison-only PR229. Existing receiver
implementation remains with S034; no production grant/STOP/model changes.
