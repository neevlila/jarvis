"""
Unit tests for Nmap XML parser (NmapScanner._parse_xml)
Tests run without an actual nmap binary — they feed synthetic XML
to the parser and verify normalised output.
"""
import pytest
from scanners.nmap_adapter.scanner import NmapScanner

MINIMAL_XML_UP = """<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94" args="nmap -sn 192.168.1.1" start="1700000000">
  <host>
    <status state="up" reason="echo-reply"/>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <hostnames><hostname name="router.local" type="PTR"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open" reason="syn-ack"/>
        <service name="ssh" product="OpenSSH" version="8.9" conf="8"/>
      </port>
      <port protocol="tcp" portid="23">
        <state state="open" reason="syn-ack"/>
        <service name="telnet" conf="7"/>
      </port>
      <port protocol="tcp" portid="8080">
        <state state="closed" reason="reset"/>
        <service name="http" conf="3"/>
      </port>
    </ports>
    <runstats><hosts up="1" down="0"/></runstats>
  </host>
</nmaprun>"""

MINIMAL_XML_DOWN = """<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
  <host>
    <status state="down" reason="no-response"/>
    <address addr="10.0.0.99" addrtype="ipv4"/>
  </host>
</nmaprun>"""

EMPTY_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.94">
</nmaprun>"""


class TestNmapXMLParsing:
    def setup_method(self):
        self.scanner = NmapScanner()

    def test_up_host_produces_asset(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        assert len(assets) == 1
        assert assets[0].ip_address == "192.168.1.1"
        assert assets[0].hostname == "router.local"
        assert assets[0].asset_type.value == "host"

    def test_down_host_produces_no_asset(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_DOWN, "job-1")
        assert len(assets) == 0

    def test_empty_xml_produces_no_assets(self):
        assets, findings, raw = self.scanner._parse_xml(EMPTY_XML, "job-1")
        assert len(assets) == 0
        assert len(findings) == 0

    def test_open_ports_produce_findings(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        # Only open ports (22 and 23) should produce findings — closed port 8080 is skipped
        assert len(findings) == 2

    def test_telnet_flagged_high_severity(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        telnet = next(f for f in findings if "telnet" in f.title.lower())
        assert telnet.severity.value == "high"

    def test_ssh_informational(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        ssh = next(f for f in findings if "ssh" in f.title.lower())
        assert ssh.severity.value == "informational"

    def test_finding_evidence_contains_version(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        ssh = next(f for f in findings if "ssh" in f.title.lower())
        assert "OpenSSH" in ssh.evidence or "8.9" in ssh.evidence

    def test_finding_confidence_from_nmap_conf(self):
        # SSH port has conf="8" → HIGH confidence
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        ssh = next(f for f in findings if "ssh" in f.title.lower())
        assert ssh.confidence.value == "high"

    def test_invalid_xml_raises_value_error(self):
        with pytest.raises(ValueError):
            self.scanner._parse_xml("<not valid xml <<", "job-x")

    def test_raw_output_contains_host_data(self):
        assets, findings, raw = self.scanner._parse_xml(MINIMAL_XML_UP, "job-1")
        assert "hosts" in raw
        assert raw["hosts"][0]["ip"] == "192.168.1.1"

    def test_scan_job_id_assigned_to_findings(self):
        _, findings, _ = self.scanner._parse_xml(MINIMAL_XML_UP, "test-job-id")
        for f in findings:
            assert f.scan_job_id == "test-job-id"

    def test_multiple_hosts(self):
        xml = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="1.1.1.1" addrtype="ipv4"/>
    <ports><port protocol="tcp" portid="80">
      <state state="open"/><service name="http" conf="5"/>
    </port></ports>
  </host>
  <host>
    <status state="up"/>
    <address addr="1.1.1.2" addrtype="ipv4"/>
    <ports><port protocol="tcp" portid="443">
      <state state="open"/><service name="https" conf="9"/>
    </port></ports>
  </host>
</nmaprun>"""
        assets, findings, raw = self.scanner._parse_xml(xml, "multi")
        assert len(assets) == 2
        assert len(findings) == 2
        ips = {a.ip_address for a in assets}
        assert "1.1.1.1" in ips
        assert "1.1.1.2" in ips
