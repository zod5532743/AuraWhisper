!macro customInit
  nsExec::ExecToStack 'cmd.exe /c "taskkill /F /IM aurawhisper.exe /T"'
  nsExec::ExecToStack 'cmd.exe /c "taskkill /F /IM python.exe /T"'
!macroend
