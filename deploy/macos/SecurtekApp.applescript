-- Securtek App (macOS) — nessuna finestra Terminale
--
-- 1) Modifica originURL con l'IP del server
-- 2) Esegui: ./deploy/macos/build-securtek-app.sh
-- 3) Usa Securtek.app sul Desktop / Dock

property originURL : "http://192.168.2.76:8000"
-- Esempio:
-- property originURL : "http://192.168.1.50:8000"

on run
	set loginURL to originURL & "/login/?app=1"
	set homePath to POSIX path of (path to home folder)
	set profileDir to homePath & "Library/Application Support/SecurtekApp"
	
	do shell script "mkdir -p " & quoted form of profileDir
	
	set chromeApp to "/Applications/Google Chrome.app"
	set edgeApp to "/Applications/Microsoft Edge.app"
	
	try
		do shell script "test -d " & quoted form of chromeApp
		set browserApp to chromeApp
	on error
		try
			do shell script "test -d " & quoted form of edgeApp
			set browserApp to edgeApp
		on error
			display alert "Securtek" message "Chrome o Edge non trovati. Installali e riprova." as critical
			return
		end try
	end try
	
	set cmd to "open -na " & quoted form of browserApp & " --args" & ¬
		" --app=" & quoted form of loginURL & ¬
		" --user-data-dir=" & quoted form of profileDir & ¬
		" --unsafely-treat-insecure-origin-as-secure=" & quoted form of originURL & ¬
		" --test-type" & ¬
		" --disable-features=InsecureDownloadWarnings"
	
	do shell script cmd
end run
