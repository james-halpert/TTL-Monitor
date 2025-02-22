from flask import Flask, render_template, request, jsonify
import threading
import time
import datetime
import dns.resolver

app = Flask(__name__)

dns_monitor_threads = {}
dns_logs = {}
dns_last_alert = {}  # Track last DNS value
dns_last_sound_alert = {}  # Prevent repeat sound alerts
dns_sound_played = {}  # Ensure start sound plays only once

def monitor_dns(domain, record_type, dns_resolver, log):
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_resolver]
        initial_response = resolver.resolve(domain, record_type)
        initial_value = " ".join([str(rdata) for rdata in initial_response])
        initial_ttl = initial_response.rrset.ttl if initial_response.rrset else 60  # Get TTL
    except Exception as e:
        log.append(f"Error: Unable to resolve {record_type} record for {domain}. {str(e)}")
        return

    log.append(f"✅ Initial {record_type} Record: {initial_value} (TTL: {initial_ttl})")

    # Play start sound once
    if not dns_sound_played.get(domain, False):
        log.append("SOUND_ALERT_START")
        dns_sound_played[domain] = True

    dns_last_alert[domain] = initial_value
    dns_last_sound_alert[domain] = initial_value  # Track last alert sound value
    dns_last_ttl[domain] = initial_ttl  # Track last TTL separately

    while True:
        try:
            response = resolver.resolve(domain, record_type)
            new_value = " ".join([str(rdata) for rdata in response])
            new_ttl = response.rrset.ttl if response.rrset else 60  # Always retrieve TTL

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if new_value != dns_last_alert[domain]:  # Only alert if the actual record value changes
                log.append(f"[{timestamp}] 🚨 CHANGE DETECTED! Old: {dns_last_alert[domain]} -> New: {new_value} (TTL: {new_ttl})")

                if dns_last_sound_alert[domain] != new_value:
                    log.append("SOUND_ALERT_CHANGE")  # Only alert if actual record changed
                    dns_last_sound_alert[domain] = new_value  # Prevent repeat alerts
                
                dns_last_alert[domain] = new_value  # Update last known value

            elif new_ttl != dns_last_ttl[domain]:  # TTL changed but value stayed the same
                log.append(f"[{timestamp}] TTL Update: {new_ttl} (Record Unchanged: {new_value})")

            dns_last_ttl[domain] = new_ttl  # Update last known TTL

        except Exception as e:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.append(f"[{timestamp}] Error querying {domain}: {str(e)}")

        time.sleep(10)  # Avoid excessive querying



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_monitor', methods=['POST'])
def start_monitor():
    domain = request.form.get('domain')
    record_type = request.form.get('record_type')
    dns_resolver = request.form.get('dns_resolver', '8.8.8.8')

    if not domain or not record_type:
        return jsonify({"error": "Missing required fields"}), 400

    if domain in dns_monitor_threads:
        return jsonify({"message": "Monitoring already in progress for this domain.", "hide_button": True})

    if domain not in dns_logs:
        dns_logs[domain] = []

    thread = threading.Thread(target=monitor_dns, args=(domain, record_type, dns_resolver, dns_logs[domain]), daemon=True)
    thread.start()
    dns_monitor_threads[domain] = thread

    return jsonify({"message": f"Started monitoring {domain} ({record_type} record) using {dns_resolver}", "hide_button": True})

@app.route('/logs/<domain>', methods=['GET'])
def get_logs(domain):
    if domain in dns_logs:
        return jsonify({"logs": dns_logs[domain]})
    return jsonify({"error": "No logs found for this domain."}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5100)
