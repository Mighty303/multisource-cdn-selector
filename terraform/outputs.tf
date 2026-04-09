output "selector_ip" {
  description = "External IP of the selector VM"
  value       = google_compute_instance.selector.network_interface[0].access_config[0].nat_ip
}

output "origin_ips" {
  description = "External IPs of all origin VMs"
  value = {
    for k, inst in google_compute_instance.origin :
    k => inst.network_interface[0].access_config[0].nat_ip
  }
}

output "origin_endpoints" {
  description = "ORIGIN_ENDPOINTS string — paste directly into env or deploy.sh"
  value = join(",", [
    for k, inst in google_compute_instance.origin :
    "${k}:http://${inst.network_interface[0].access_config[0].nat_ip}"
  ])
}

output "admin_endpoints" {
  description = "Selector admin API URLs"
  value = {
    mode    = "http://${google_compute_instance.selector.network_interface[0].access_config[0].nat_ip}/admin/mode?value=adaptive"
    failure = "http://${google_compute_instance.selector.network_interface[0].access_config[0].nat_ip}/admin/failure?origin=<id>&duration=${var.selector_failure_duration}"
  }
}

output "verify_commands" {
  description = "Commands to verify the deployment after running deploy.sh"
  value       = <<-EOT
    # Health + status checks
    curl http://${google_compute_instance.selector.network_interface[0].access_config[0].nat_ip}/health
    curl http://${google_compute_instance.selector.network_interface[0].access_config[0].nat_ip}/api/status | python3 -m json.tool

    # Run integration tests (requires deploy.sh to have been run first)
    export GCP_PROJECT=${var.project_id}
    export SELECTOR_VM=dash-selector-iowa
    export SELECTOR_ZONE=us-central1-a
    export SELECTOR_BASE_URL=http://${google_compute_instance.selector.network_interface[0].access_config[0].nat_ip}
    export ORIGIN_VMS=oregon:dash-origin-oregon:us-west1-b,toronto:dash-origin-toronto:northamerica-northeast2-a,ncalifornia:dash-origin-ncalifornia:us-west2-b
    export ORIGIN_ENDPOINTS=${join(",", [for k, inst in google_compute_instance.origin : "${k}:http://${inst.network_interface[0].access_config[0].nat_ip}"])}
    bash tests/test_segments.sh
    bash tests/test_routing.sh
  EOT
}
