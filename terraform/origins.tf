locals {
  origins = {
    oregon = {
      vm_name      = "dash-origin-oregon"
      zone         = "us-west1-b"
      region_label = "Oregon"
      origin_id    = "oregon"
    }
    toronto = {
      vm_name      = "dash-origin-toronto"
      zone         = "northamerica-northeast2-a"
      region_label = "Toronto"
      origin_id    = "toronto"
    }
    ncalifornia = {
      vm_name      = "dash-origin-ncalifornia"
      zone         = "us-west2-b"
      region_label = "Northern California"
      origin_id    = "ncalifornia"
    }
  }
}

resource "google_compute_instance" "origin" {
  for_each     = local.origins
  name         = each.value.vm_name
  machine_type = local.machine_type
  zone         = each.value.zone

  tags = [local.vm_tag]

  boot_disk {
    initialize_params {
      image = local.image
    }
  }

  network_interface {
    network = "default"
    access_config {} # ephemeral external IP
  }

  metadata = {
    startup-script = templatefile("${path.module}/templates/origin_startup.sh.tpl", {
      origin_id    = each.value.origin_id
      region_label = each.value.region_label
    })
  }

  service_account {
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/pubsub",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append",
    ]
  }
}
