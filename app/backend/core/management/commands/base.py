"""
Base Rich Command

Foundation class for Django management commands with Rich CLI formatting.
Provides colored output, tables, panels, progress bars, and safety features.
"""

from contextlib import contextmanager
from django.core.management.base import BaseCommand
from django.db import transaction
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn


class BaseRichCommand(BaseCommand):
    """
    Enhanced BaseCommand with Rich formatting and safety features.

    Features:
    - Colored output (success=green, error=red, warning=yellow, info=blue)
    - Formatted tables and panels
    - Progress bars
    - Interactive confirmations
    - Dry-run support
    - Atomic transactions

    Subclasses should override execute() instead of handle().
    """

    # Configuration flags (override in subclasses)
    requires_confirmation = False  # Ask "Are you sure?" before execution
    supports_dry_run = True       # Support --dry-run flag
    use_atomic_transaction = True # Wrap execution in transaction.atomic()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize console immediately (will be reconfigured in handle())
        self.console = Console()
        self.is_dry_run = False
        self.force = False
        self.no_color = False

    def add_arguments(self, parser):
        """
        Add standard arguments that all commands support.
        Subclasses can override to add more arguments.

        Note: --no-color is already provided by Django's BaseCommand
        """
        if self.supports_dry_run:
            parser.add_argument(
                '--dry-run',
                action='store_true',
                help='Preview changes without executing them'
            )

        if self.requires_confirmation:
            parser.add_argument(
                '--force',
                action='store_true',
                help='Skip confirmation prompts'
            )

    def handle(self, *args, **options):
        """
        Framework wrapper that handles:
        - Console setup
        - Flag parsing
        - Confirmations
        - Transactions
        - Error handling

        Do NOT override this method. Override execute() instead.
        """
        # Parse options
        self.is_dry_run = options.get('dry_run', False)
        self.force = options.get('force', False)
        self.no_color = options.get('no_color', False)

        # Setup Rich console
        self.console = Console(no_color=self.no_color)

        # Show dry-run warning
        if self.is_dry_run:
            self.warning("DRY RUN MODE - No changes will be made")

        # Handle confirmation
        if self.requires_confirmation and not self.force and not self.is_dry_run:
            if not self.confirm("This operation may modify data. Continue?"):
                self.info("Operation cancelled by user")
                return

        # Execute with error handling
        try:
            if self.use_atomic_transaction and not self.is_dry_run:
                with transaction.atomic():
                    self.execute(*args, **options)
            else:
                self.execute(*args, **options)
        except KeyboardInterrupt:
            self.error("\nOperation cancelled by user (Ctrl+C)")
            raise SystemExit(1)
        except Exception as e:
            self.error(f"Command failed: {str(e)}")
            if options.get('verbosity', 1) >= 2:
                import traceback
                self.console.print_exception()
            raise

    def execute(self, *args, **options):
        """
        Main command logic. Subclasses MUST implement this method.

        This is called by handle() after all safety checks and setup.
        Use self.success(), self.error(), etc. for output.
        Use self.is_dry_run to check if in dry-run mode.
        """
        raise NotImplementedError("Subclasses must implement execute()")

    # ========== Output Methods ==========

    def success(self, message):
        """Print success message in green"""
        self.console.print(f"✓ {message}", style="bold green")

    def error(self, message):
        """Print error message in red"""
        self.console.print(f"✗ {message}", style="bold red")

    def warning(self, message):
        """Print warning message in yellow"""
        self.console.print(f"⚠ {message}", style="bold yellow")

    def info(self, message):
        """Print info message in blue"""
        self.console.print(f"ℹ {message}", style="bold blue")

    def print(self, message, style=None):
        """Print plain message (optionally styled)"""
        self.console.print(message, style=style)

    # ========== Formatting Methods ==========

    def panel(self, title, content, style="bold"):
        """
        Display content in a bordered panel.

        Args:
            title: Panel title
            content: Content to display (can be multi-line string)
            style: Border style (default: "bold")
        """
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)

    def table(self, title, headers, rows, show_header=True):
        """
        Display data as a formatted table.

        Args:
            title: Table title
            headers: List of column headers
            rows: List of row data (each row is a list matching headers)
            show_header: Show header row (default: True)

        Example:
            self.table(
                "Users",
                ["ID", "Email", "Status"],
                [
                    [1, "user1@example.com", "Active"],
                    [2, "user2@example.com", "Inactive"]
                ]
            )
        """
        table = Table(title=title, show_header=show_header)

        # Add columns
        for header in headers:
            table.add_column(header, style="cyan")

        # Add rows
        for row in rows:
            table.add_row(*[str(cell) for cell in row])

        self.console.print(table)

    @contextmanager
    def progress(self, description="Processing..."):
        """
        Context manager for progress bars.

        Usage:
            with self.progress("Processing users") as progress:
                task = progress.add_task("[cyan]Processing...", total=total_count)
                for item in items:
                    # Do work
                    progress.advance(task)
        """
        progress_bar = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        with progress_bar as progress:
            yield progress

    def confirm(self, question):
        """
        Ask user for yes/no confirmation.

        Args:
            question: Question to ask

        Returns:
            True if user confirms, False otherwise

        Note: Always returns True if --force flag is set
        """
        if self.force:
            return True

        response = self.console.input(f"[bold yellow]?[/bold yellow] {question} [y/N]: ")
        return response.lower() in ['y', 'yes']

    # ========== Helper Methods ==========

    def get_or_create_summary(self):
        """
        Helper to create a summary dict for tracking operations.
        Useful for displaying statistics at the end of command execution.
        """
        return {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'skipped': 0,
            'errors': 0,
        }

    def display_summary(self, summary, title="Summary"):
        """
        Display operation summary in a panel.

        Args:
            summary: Dict with operation counts (created, updated, deleted, etc.)
            title: Panel title
        """
        lines = []
        for key, value in summary.items():
            emoji = "✓" if key != "errors" else "✗"
            color = "green" if key != "errors" else "red"
            lines.append(f"[{color}]{emoji} {key.title()}: {value}[/{color}]")

        content = "\n".join(lines)
        self.panel(title, content)
