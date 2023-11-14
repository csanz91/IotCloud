#!/bin/ash
echo 'Starting backups upload'

backup_folder=`cat /run/secrets/gdrive_backup_folder`
#gdrive -c / --service-account /run/secrets/gdrive_config sync upload --delete-extraneous /backups/ $backup_folder
while true; do
	status=$(gdrive -c / --service-account /run/secrets/gdrive_config sync upload --keep-local --delete-extraneous /backups/ $backup_folder)
	if echo "$status" | grep -q "Found name collision between"; then
		statusLine=$(echo "$status" | grep "Found name collision between" | sed "s/.*Found name/Found name/g")
		echo "found same file name!!"
		echo "$statusLine"
		file=$(echo "$statusLine" | sed "s/Found name collision between //g" | sed "s/\ and\ /,/g")
		file1=$(echo "$file" | cut -d ',' -f 1)
		file2=$(echo $file1 | cut -d ' ' -f1)

		echo "same file: $file"
		echo "deleting file: $file2"
		gdrive -c / --service-account /run/secrets/gdrive_config delete -r "$file2"

		
	elif echo "$status" | grep -q "Could not find parent of"; then
		statusLine=$(echo "$status" | grep "Could not find parent of" | sed "s/.*Found name/Found name/g")
		echo "found same file name!!"
		echo "$statusLine"
		file=$(echo "$statusLine" | sed "s/Could not find parent of //g" | sed "s/\ and\ /,/g")
		file1=$(echo "$file" | cut -d ',' -f 1)
		file2=$(echo $file1 | cut -d ' ' -f1)

		echo "same file: $file"
		echo "deleting file: $file2"
		gdrive -c / --service-account /run/secrets/gdrive_config delete -r "$file2"
	else


		echo "not filename collision"
		echo "message:"
		echo "$status"
		break
	fi
	sleep 10
done
		
