.PHONY: all
all: init fmt validate build

.PHONY: init
init: 
	terraform init	

.PHONY: fmt
fmt: 
	terraform fmt

.PHONY: validate
validate: 
	terraform validate
	
.PHONY: build
build: 
	terraform apply

.PHONY: destroy
destroy: 
	terraform destroy
