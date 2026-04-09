locals {
  # Build id → "http://IP" map from live origin instance IPs.
  # Terraform resolves this AFTER origin VMs are created (implicit dependency).
  origin_endpoints_map = {
    for k, inst in google_compute_instance.origin :
    k => "http://${inst.network_interface[0].access_config[0].nat_ip}"
  }

  # Pre-serialized JSON array passed to the template to avoid trailing-comma issues
  # when using HCL for loops inside template files.
  origins_json = jsonencode([
    for k, url in local.origin_endpoints_map : {
      id       = k
      base_url = url
    }
  ])
}

resource "google_compute_instance" "selector" {
  name         = "dash-selector-iowa"
  machine_type = local.machine_type
  zone         = "us-central1-a"

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
    startup-script = templatefile("${path.module}/templates/selector_startup.sh.tpl", {
      selector_port         = 80
      selector_mode         = var.selector_mode
      weight_latency        = var.weight_latency
      weight_load           = var.weight_load
      weight_throughput     = var.weight_throughput
      probe_timeout_seconds = var.probe_timeout_seconds
      probe_ttl_seconds     = var.probe_ttl_seconds
      probe_sample_bytes    = var.probe_sample_bytes
      origins_json          = local.origins_json
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

  # Origin IPs are interpolated into the startup script above, which already
  # creates an implicit dependency. This explicit depends_on makes the ordering
  # visible and ensures Terraform never attempts to create the selector in parallel.
  depends_on = [google_compute_instance.origin]
}
