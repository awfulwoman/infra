# Home Network

This will provide a domain for my home network and create all necessary subdomains.

## Usage

Export necessary secrets variables.
```
export TF_VAR_digitalocean_token=WHATEVER
export TF_VAR_domain_name=WHATEVER
```

Log in to Terraform Cloud if you have not done so.
```
terraform init
```

Initialise Terraform and downlaod dependencies.
```
terraform init
```

Plan and apply Terraform.
```
terraform plan
terraform apply
```