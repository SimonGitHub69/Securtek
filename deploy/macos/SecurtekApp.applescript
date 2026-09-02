-- Securtek App (macOS) — Edge/Chrome in modalità --app (finestra dedicata)
--
-- 1) Modifica originURL con l'IP del server
-- 2) browserChoice: "edge" | "chrome"
-- 3) Esegui: ./deploy/macos/build-securtek-app.sh

property originURL : "http://192.168.2.76:8000"
property browserChoice : "edge"

on run
	set loginURL to originURL & "/login/?app=1"
	set homePath to POSIX path of (path to home folder)
	set profileDir to homePath & "Library/Application Support/SecurtekApp"
	set appFlags to " --no-first-run --no-default-browser-check --no-startup-window --disable-session-crashed-bubble --disable-features=TranslateUI"
	
	do shell script "mkdir -p " & quoted form of profileDir
	
	if browserChoice is "chrome" then
		try
			set chromeBin to "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
			do shell script "test -x " & quoted form of chromeBin
			set cmd to quoted form of chromeBin & " --app=" & quoted form of loginURL & " --user-data-dir=" & quoted form of profileDir & appFlags & " >/dev/null 2>&1 &"
			do shell script cmd
			return
		end try
	end if
	
	try
		set edgeBin to "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
		do shell script "test -x " & quoted form of edgeBin
		set cmd to quoted form of edgeBin & " --app=" & quoted form of loginURL & " --user-data-dir=" & quoted form of profileDir & appFlags & " >/dev/null 2>&1 &"
		do shell script cmd
		return
	end try
	
	try
		set chromeBin to "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
		do shell script "test -x " & quoted form of chromeBin
		set cmd to quoted form of chromeBin & " --app=" & quoted form of loginURL & " --user-data-dir=" & quoted form of profileDir & appFlags & " >/dev/null 2>&1 &"
		do shell script cmd
		return
	end try
	
	display alert "Securtek" message "Installa Microsoft Edge o Google Chrome." as critical
end run
