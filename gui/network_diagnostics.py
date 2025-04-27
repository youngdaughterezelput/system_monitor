import psutil
import socket
import subprocess
import re
from typing import Dict, List, Optional, Tuple

class NetworkDiagnostics:
    @staticmethod
    def get_connections() -> List[Dict]:
        """Get all network connections"""
        connections = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status:
                connections.append({
                    'family': conn.family.name,
                    'type': conn.type.name,
                    'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status,
                    'pid': conn.pid
                })
        return connections

    @staticmethod
    def ping_host(host: str, count: int = 4) -> Dict:
        """Ping a host and return results"""
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", str(count), host]
            else:
                cmd = ["ping", "-c", str(count), host]
                
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            return {
                'success': True,
                'output': output,
                'stats': NetworkDiagnostics._parse_ping(output)
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'output': e.output,
                'error': str(e)
            }

    @staticmethod
    def _parse_ping(output: str) -> Dict:
        """Parse ping command output"""
        stats = {}
        # Parse packet loss
        packet_loss = re.search(r'(\d+)% packet loss', output)
        if packet_loss:
            stats['packet_loss'] = int(packet_loss.group(1))
        
        # Parse round-trip times
        rtt = re.search(r'= (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms', output)
        if rtt:
            stats['rtt_min'] = float(rtt.group(1))
            stats['rtt_avg'] = float(rtt.group(2))
            stats['rtt_max'] = float(rtt.group(3))
            stats['rtt_mdev'] = float(rtt.group(4))
        
        return stats

    @staticmethod
    def trace_route(host: str) -> Dict:
        """Perform traceroute to a host"""
        try:
            if platform.system().lower() == "windows":
                cmd = ["tracert", "-d", host]
            else:
                cmd = ["traceroute", "-n", host]
                
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            return {
                'success': True,
                'output': output,
                'hops': NetworkDiagnostics._parse_trace(output)
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'output': e.output,
                'error': str(e)
            }

    @staticmethod
    def _parse_trace(output: str) -> List[Dict]:
        """Parse traceroute output"""
        hops = []
        # Windows format
        if platform.system().lower() == "windows":
            for line in output.split('\n')[2:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    hops.append({
                        'hop': int(parts[0]),
                        'ip': parts[-1],
                        'times': [float(t.replace('<', '')) for t in parts[1:-1] if t != 'ms']
                    })
        # Linux format
        else:
            for line in output.split('\n')[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    hops.append({
                        'hop': int(parts[0]),
                        'ip': parts[1],
                        'times': [float(t) for t in parts[2:] if t != '*']
                    })
        return hops

    def get_network_stats(self) -> Dict:
        """Get comprehensive network statistics"""
        io = psutil.net_io_counters()
        return {
            'bytes_sent': io.bytes_sent,
            'bytes_recv': io.bytes_recv,
            'packets_sent': io.packets_sent,
            'packets_recv': io.packets_recv,
            'errin': io.errin,
            'errout': io.errout,
            'dropin': io.dropin,
            'dropout': io.dropout
        }