#! /bin/bash
server_alias="csanz1"
ota_bin_path="$(realpath "$1")"
model_num="$2"
version="$3"
parent_path="IotCloud/ota/data/$model_num"
bin_bath="$parent_path/$version"

echo "Creating directory '$parent_path' on the server..."
ssh csanz1 "mkdir -p $parent_path"

echo "Coping '$ota_bin_path' to the server..."
scp $ota_bin_path $server_alias:$bin_bath

echo "Changing permissions of the binary file..."
ssh csanz1 "chmod 755 $bin_bath"

echo "Requesting OTA update start"
mosquitto_pub -h mqtt.iotcloud.es -t "v1/ota/update/$model_num" -u "secret_token" -P "_" -m "$version"