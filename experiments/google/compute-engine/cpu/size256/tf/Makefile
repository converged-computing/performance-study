.PHONY: all
all: init fmt validate deploy

.PHONY: init
init: 
	terraform init
	
.PHONY: fmt
fmt: 
	terraform fmt

.PHONY: validate
validate: 
	terraform validate

.PHONY: template
template:
	cp ./scripts/boot_script.sh ./boot_script_generated.sh
	sed -i "s/NODELIST/${NODELIST}/g" ./boot_script_generated.sh
	
.PHONY: deploy
deploy: 
	export GOOGLE_PROJECT=$(gcloud config get-value core/project)
	terraform apply -var-file basic.tfvars -var region=us-central1 -var project_id=$(gcloud config get-value core/project) -var network_name=foundation-net -var zone=us-central1-a

.PHONY: destroy
destroy: 
	export GOOGLE_PROJECT=$(gcloud config get-value core/project)
	terraform destroy -var-file basic.tfvars -var region=us-central1 -var project_id=$(gcloud config get-value core/project) -var network_name=foundation-net -var zone=us-central1-a
