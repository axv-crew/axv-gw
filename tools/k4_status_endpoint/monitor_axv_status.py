#!/usr/bin/env python3
"""
monitor_axv_status.py - Continuous monitoring of AXV status endpoint

Usage:
    python monitor_axv_status.py
    python monitor_axv_status.py --url http://api.axv.life
    python monitor_axv_status.py --interval 30 --alert-webhook https://hooks.slack.com/...
"""

import argparse
import asyncio
import time
from datetime import datetime
from typing import Optional
import httpx
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

console = Console()

# ============================================================================
# Configuration
# ============================================================================

class MonitorConfig:
    def __init__(
        self,
        url: str = "http://localhost:8080/axv/status",
        interval: int = 15,
        alert_webhook: Optional[str] = None,
        alert_on_degraded: bool = False,
    ):
        self.url = url
        self.interval = interval
        self.alert_webhook = alert_webhook
        self.alert_on_degraded = alert_on_degraded


# ============================================================================
# Status Tracker
# ============================================================================

class StatusTracker:
    def __init__(self):
        self.history = []
        self.max_history = 100
        self.last_alert = {}
        self.alert_cooldown = 300  # 5 minutes
        
    def add_status(self, status: dict):
        """Add status to history"""
        self.history.append({
            "timestamp": datetime.now(),
            "status": status
        })
        
        # Keep only last N entries
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def should_alert(self, component: str, status: str) -> bool:
        """Check if we should send alert for this component"""
        now = time.time()
        
        # Check cooldown
        if component in self.last_alert:
            if now - self.last_alert[component] < self.alert_cooldown:
                return False
        
        # Update last alert time
        self.last_alert[component] = now
        return True
    
    def get_stats(self) -> dict:
        """Calculate statistics from history"""
        if not self.history:
            return {}
        
        total = len(self.history)
        ok_count = sum(1 for h in self.history if h["status"].get("ok"))
        
        return {
            "total_checks": total,
            "ok_count": ok_count,
            "uptime_percentage": (ok_count / total) * 100 if total > 0 else 0,
            "last_check": self.history[-1]["timestamp"] if self.history else None,
        }


# ============================================================================
# Alerting
# ============================================================================

async def send_alert(
    webhook_url: str,
    component: str,
    status: str,
    message: str
):
    """Send alert to webhook (Slack, Discord, etc.)"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "text": f"🚨 AXV Alert: {component}",
                "attachments": [
                    {
                        "color": "danger" if status == "down" else "warning",
                        "fields": [
                            {
                                "title": "Component",
                                "value": component,
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": status,
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": message,
                                "short": False
                            }
                        ],
                        "footer": "AXV Monitoring",
                        "ts": int(time.time())
                    }
                ]
            }
            
            await client.post(webhook_url, json=payload, timeout=5.0)
            console.print(f"[yellow]Alert sent for {component}[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to send alert: {e}[/red]")


# ============================================================================
# Monitoring Loop
# ============================================================================

async def fetch_status(config: MonitorConfig) -> Optional[dict]:
    """Fetch status from endpoint"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(config.url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        console.print(f"[red]Error fetching status: {e}[/red]")
        return None


def create_status_table(status: dict) -> Table:
    """Create Rich table from status data"""
    table = Table(title="AXV Component Status")
    
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")
    
    # Add components
    for component, component_status in status.get("status", {}).items():
        # Color based on status
        if component_status == "ok":
            status_style = "[green]●[/green] OK"
        elif component_status == "degraded":
            status_style = "[yellow]●[/yellow] DEGRADED"
        elif component_status == "down":
            status_style = "[red]●[/red] DOWN"
        else:
            status_style = "[dim]●[/dim] UNKNOWN"
        
        table.add_row(
            component.upper(),
            status_style,
            ""
        )
    
    return table


def create_nodes_table(status: dict) -> Table:
    """Create Rich table for nodes"""
    table = Table(title="Cluster Nodes")
    
    table.add_column("ID", style="cyan")
    table.add_column("Role", style="blue")
    table.add_column("Host", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("Age", style="dim")
    
    nodes = status.get("nodes", [])
    if not nodes:
        table.add_row("—", "—", "—", "[dim]No nodes[/dim]", "—")
        return table
    
    for node in nodes:
        node_status = node.get("status", "unknown")
        if node_status == "ok":
            status_style = "[green]●[/green] OK"
        elif node_status == "degraded":
            status_style = "[yellow]●[/yellow] DEGRADED"
        elif node_status == "down":
            status_style = "[red]●[/red] DOWN"
        else:
            status_style = "[dim]●[/dim] UNKNOWN"
        
        table.add_row(
            node.get("id", "?"),
            node.get("role", "?"),
            node.get("host", "?"),
            status_style,
            f"{node.get('age_s', 0)}s"
        )
    
    return table


def create_stats_panel(tracker: StatusTracker) -> Panel:
    """Create statistics panel"""
    stats = tracker.get_stats()
    
    if not stats:
        return Panel("No data yet", title="Statistics")
    
    content = f"""
[bold]Total Checks:[/bold] {stats['total_checks']}
[bold]OK Count:[/bold] {stats['ok_count']}
[bold]Uptime:[/bold] {stats['uptime_percentage']:.1f}%
[bold]Last Check:[/bold] {stats['last_check'].strftime('%H:%M:%S') if stats['last_check'] else 'N/A'}
"""
    
    return Panel(content, title="Statistics")


async def monitor_loop(config: MonitorConfig):
    """Main monitoring loop"""
    tracker = StatusTracker()
    
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            # Fetch status
            status = await fetch_status(config)
            
            if status:
                # Add to history
                tracker.add_status(status)
                
                # Check for alerts
                if config.alert_webhook:
                    overall_ok = status.get("ok", True)
                    overall_status = status.get("overall_status")
                    
                    # Alert on down
                    if not overall_ok:
                        for component, component_status in status.get("status", {}).items():
                            if component_status == "down":
                                if tracker.should_alert(component, component_status):
                                    await send_alert(
                                        config.alert_webhook,
                                        component,
                                        component_status,
                                        f"{component} is DOWN!"
                                    )
                    
                    # Alert on degraded (if enabled)
                    if config.alert_on_degraded and overall_status == "degraded":
                        for component, component_status in status.get("status", {}).items():
                            if component_status == "degraded":
                                if tracker.should_alert(component, component_status):
                                    await send_alert(
                                        config.alert_webhook,
                                        component,
                                        component_status,
                                        f"{component} is DEGRADED"
                                    )
                
                # Create layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="body"),
                    Layout(name="footer", size=8)
                )
                
                # Header
                overall_ok = status.get("ok", True)
                overall_status = status.get("overall_status")
                
                if overall_ok and not overall_status:
                    header_text = "[green bold]✓ AXV System: OK[/green bold]"
                elif overall_ok and overall_status == "degraded":
                    header_text = "[yellow bold]⚠ AXV System: DEGRADED[/yellow bold]"
                else:
                    header_text = "[red bold]✗ AXV System: DOWN[/red bold]"
                
                layout["header"].update(
                    Panel(
                        f"{header_text} | Version: {status.get('version')} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        style="bold"
                    )
                )
                
                # Body - split between components and nodes
                layout["body"].split_row(
                    Layout(create_status_table(status), name="components"),
                    Layout(create_nodes_table(status), name="nodes")
                )
                
                # Footer
                layout["footer"].update(create_stats_panel(tracker))
                
                # Update display
                live.update(layout)
            else:
                live.update(Panel(
                    "[red]Failed to fetch status[/red]",
                    title="Error"
                ))
            
            # Wait for next check
            await asyncio.sleep(config.interval)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Monitor AXV status endpoint continuously"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080/axv/status",
        help="Status endpoint URL"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Check interval in seconds (default: 15)"
    )
    parser.add_argument(
        "--alert-webhook",
        help="Webhook URL for alerts (Slack, Discord, etc.)"
    )
    parser.add_argument(
        "--alert-on-degraded",
        action="store_true",
        help="Send alerts for degraded status (not just down)"
    )
    
    args = parser.parse_args()
    
    config = MonitorConfig(
        url=args.url,
        interval=args.interval,
        alert_webhook=args.alert_webhook,
        alert_on_degraded=args.alert_on_degraded,
    )
    
    console.print(f"[bold]Starting AXV Status Monitor[/bold]")
    console.print(f"URL: {config.url}")
    console.print(f"Interval: {config.interval}s")
    if config.alert_webhook:
        console.print(f"Alerts: Enabled")
    console.print("")
    
    try:
        asyncio.run(monitor_loop(config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


if __name__ == "__main__":
    main()
