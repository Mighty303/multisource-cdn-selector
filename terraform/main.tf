terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials_file)
  project     = var.project_id
  region      = "us-central1"
}

locals {
  machine_type = "e2-micro"
  image        = "debian-cloud/debian-12"
  vm_tag       = "http-server"
}

resource "google_compute_firewall" "allow_http" {
  name    = "default-allow-http"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = [local.vm_tag]
}
