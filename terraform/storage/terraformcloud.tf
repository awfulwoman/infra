terraform {
  cloud {
    organization = "whalecoiner"

    workspaces {
      name = "domains"
    }
  }
}
