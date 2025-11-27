#!/bin/bash

project_id="$(gcloud config get-value core/project)"
main_bucket="${1}"
variables_bucket="${project_id}_variables"

if [[ "${main_bucket}" == "" ]]; then
    echo "Please provide the name of your main bucket as the first input."
    exit
fi

gcloud storage buckets create gs://${main_bucket} || echo "${main_bucket} already exists?"
gcloud storage buckets create gs://${variables_bucket} || echo "${variables_bucket} already exists?"

gcloud storage cp ./main.tf gs://${main_bucket}
gcloud storage cp ./variables.tf gs://${variables_bucket}

# --implicit-dirs is only needed if you have existing nested files you want to see
cat << EOF > ./fuse-mounts.sh
#!/bin/bash

mkdir /mnt/workflow
gcsfuse -o ro,allow_other --implicit-dirs ${main_bucket} /mnt/workflow

mkdir /mnt/variables
gcsfuse -o rw,allow_other --implicit-dirs ${variables_bucket} /mnt/variables
EOF
