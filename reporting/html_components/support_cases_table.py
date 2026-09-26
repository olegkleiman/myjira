"""
Support Cases SLA Table - HTML generation for support cases metrics
"""

from typing import List, Dict
from models import SupportCasesMetrics

from .base_generator import highlight_attrs

class SupportCasesTableGenerator:
    """Generates HTML table for support cases SLA metrics"""

    def generate_table(self, metrics_by_squad: Dict[str, List[SupportCasesMetrics]]) -> str:
        """
        Generate HTML table for support cases SLA metrics.

        Args:
            metrics_by_squad: Dict mapping squad names to list of SupportCasesMetrics
                             (list contains squad-level aggregate + project-level breakdowns)

        Returns:
            HTML string for the support cases table
        """
        if not metrics_by_squad:
            return ""

        html = []
        html.append('<table style="width: 100%; font-family: Arial, sans-serif;">')

        # Table header (highlight attrs replace background-color - Cloud strips arbitrary CSS backgrounds)
        header_attrs = highlight_attrs("blue")
        html.append('<thead>')
        html.append('<tr>')
        html.append(f'  <th style="text-align: left; font-weight: bold; padding: 10px;"{header_attrs}>Squad / Project</th>')
        html.append(f'  <th style="text-align: center; font-weight: bold;"{header_attrs}>Ingress</th>')
        html.append(f'  <th style="text-align: center; font-weight: bold;"{header_attrs}>Egress</th>')
        html.append(f'  <th style="text-align: center; font-weight: bold;"{header_attrs}>Net Change</th>')
        html.append('</tr>')
        html.append('</thead>')

        # Table body
        html.append('<tbody>')

        for squad_name, metrics_list in metrics_by_squad.items():
            # group metrics by project (None = squad aggregate)
            grouped: Dict[str, Dict[str, SupportCasesMetrics]] = {}
            for m in metrics_list:
                key = m.project_name or "__squad__"
                grouped.setdefault(key, {})[m.environment] = m

            # Squad aggregate row (no separate header)
            squad_env = grouped.get("__squad__", {})
            combined = self._combine_env_metrics(squad_env.get("production"), squad_env.get("non_production"), squad_name, None)
            if combined:
                html.append(self._generate_row(combined, level="squad"))

            # Project rows
            for project_name, env_map in grouped.items():
                if project_name == "__squad__":
                    continue
                combined = self._combine_env_metrics(env_map.get("production"), env_map.get("non_production"), squad_name, project_name)
                if combined:
                    html.append(self._generate_row(combined, level="project"))

        html.append('</tbody>')
        html.append('</table>')

        return '\n'.join(html)

    def _combine_env_metrics(
        self,
        prod: SupportCasesMetrics,
        non_prod: SupportCasesMetrics,
        squad_name: str,
        project_name: str,
    ) -> Dict:
        # Normalize missing metrics
        def zero_metrics(env: str) -> SupportCasesMetrics:
            return SupportCasesMetrics(
                squad_name=squad_name,
                project_name=project_name,
                environment=env,
                ingress=0,
                egress=0,
                cases=[],
            )

        prod = prod or zero_metrics("production")
        non_prod = non_prod or zero_metrics("non_production")

        ingress = prod.ingress + non_prod.ingress
        egress = prod.egress + non_prod.egress
        net_change = ingress - egress

        # Bold non-zero values so they stand out from the zero baseline; render zero as a dash
        def bold_if_nonzero(value: int, signed: bool = False) -> str:
            if value == 0:
                return "-"
            text = f"{value:+d}" if signed else str(value)
            return f"<b>{text}</b>"

        def format_net(p_net, n_net, total_net):
            return (
                f"p:{bold_if_nonzero(p_net, signed=True)} "
                f"n:{bold_if_nonzero(n_net, signed=True)} "
                f"t:{bold_if_nonzero(total_net, signed=True)}"
            )

        return {
            "squad_name": squad_name,
            "project_name": project_name,
            "ingress_text": f"p:{bold_if_nonzero(prod.ingress)} n:{bold_if_nonzero(non_prod.ingress)} t:{bold_if_nonzero(ingress)}",
            "egress_text": f"p:{bold_if_nonzero(prod.egress)} n:{bold_if_nonzero(non_prod.egress)} t:{bold_if_nonzero(egress)}",
            "net_change_text": format_net(prod.net_change, non_prod.net_change, net_change),
            "net_change_value": net_change,
        }

    def _generate_row(self, combined: Dict, level: str = "squad") -> str:
        """Generate a single table row for support cases metrics (combined prod/non-prod)."""
        # Determine label and styling based on hierarchy level
        if level == "project":
            label = f"  └─ {combined.get('project_name') or ''}".rstrip()
            label_attrs = ' style="padding-left: 30px;"'
        else:
            label = combined['squad_name']
            label_attrs = ' style="font-weight: bold;"' + highlight_attrs("grey")

        net_change = combined.get("net_change_value", 0)

        # Color code net change (positive = backlog growing = red, negative = backlog shrinking = green)
        if net_change > 0:
            net_change_attrs = highlight_attrs("red")
        elif net_change < 0:
            net_change_attrs = highlight_attrs("green")
        else:
            net_change_attrs = highlight_attrs("yellow")

        row = []
        row.append('<tr>')
        row.append(f'  <td{label_attrs}>{label}</td>')
        row.append(f'  <td style="text-align: center;">{combined["ingress_text"]}</td>')
        row.append(f'  <td style="text-align: center;">{combined["egress_text"]}</td>')
        row.append(f'  <td style="text-align: center;"{net_change_attrs}>{combined["net_change_text"]}</td>')
        row.append('</tr>')

        return '\n'.join(row)
