"""CLI commands untuk stock screening application.

Module ini berisi semua command-line interface commands menggunakan Click.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.__version__ import __version__
from src.analyzers.fundamental_analyzer import FundamentalAnalyzer
from src.services.news_scraper_service import NewsScraperService
from src.services.yahoo_finance_service import YahooFinanceService
from src.utils.helpers import (
    format_currency,
    format_number,
    format_percentage,
    format_ratio,
    get_ticker_without_suffix,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()

# Constants
MIN_COMPARISON_TICKERS = 2


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="Friday Screener")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Friday Screener - Stock Screening Tool for Indonesian Market.

    Professional-grade stock screening tool untuk analisis fundamental
    emiten saham di Bursa Efek Indonesia.
    """
    if ctx.invoked_subcommand is None:
        # Jika tidak ada subcommand, jalankan interactive mode
        ctx.invoke(interactive)


@cli.command()
@click.argument("ticker")
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed analysis including all insights",
)
@click.option(
    "--news/--no-news",
    default=True,
    help="Include news and corporate actions (default: yes)",
)
def screen(ticker: str, detailed: bool, news: bool) -> None:
    """Screen a stock ticker untuk analisis fundamental.

    TICKER: Kode emiten saham (contoh: BBCA, TLKM, ASII)

    Contoh penggunaan:

        friday-screener screen BBCA

        friday-screener screen TLKM --detailed

        friday-screener screen ASII --no-news
    """
    console.print(f"\n[bold cyan]Screening {ticker.upper()}...[/bold cyan]\n")

    # Initialize services
    finance_service = YahooFinanceService()
    news_service = NewsScraperService(max_news=10)
    analyzer = FundamentalAnalyzer()

    # Step 1: Fetch stock data
    with console.status(f"[bold green]Fetching data for {ticker}..."):
        stock_data = finance_service.get_stock_data(ticker)

    if stock_data is None:
        console.print(
            f"[bold red]Error:[/bold red] Could not fetch data for {ticker}. "
            "Please check the ticker symbol.",
        )
        return

    # Step 2: Fetch news if requested
    news_items = []
    corporate_actions = []
    if news:
        with console.status("[bold green]Fetching news and corporate actions..."):
            news_items = news_service.get_news(ticker)
            corporate_actions = news_service.get_corporate_actions(ticker)

        # Add to stock data
        stock_data.news = news_items
        stock_data.corporate_actions = corporate_actions

    # Step 3: Analyze
    with console.status("[bold green]Analyzing fundamental metrics..."):
        result = analyzer.analyze(stock_data)

    # Display results
    _display_company_info(stock_data)
    _display_screening_summary(result)
    _display_category_scores(result)

    if detailed:
        _display_key_metrics(result)
        _display_insights(result)

    if news:
        _display_news_summary(news_items, corporate_actions, news_service)

    _display_recommendation(result)


@cli.command()
@click.argument("tickers", nargs=-1, required=True)
def compare(tickers: tuple[str, ...]) -> None:
    """Compare multiple stocks side by side.

    TICKERS: Dua atau lebih kode emiten (contoh: BBCA BMRI BBNI)

    Contoh penggunaan:

        friday-screener compare BBCA BMRI BBNI
    """
    if len(tickers) < MIN_COMPARISON_TICKERS:
        console.print(
            "[bold red]Error:[/bold red] Please provide at least 2 tickers to compare",
        )
        return

    console.print(
        f"\n[bold cyan]Comparing {len(tickers)} stocks...[/bold cyan]\n",
    )

    # Initialize services
    finance_service = YahooFinanceService()
    analyzer = FundamentalAnalyzer()

    results = []

    # Fetch and analyze each stock
    for ticker in tickers:
        with console.status(f"[bold green]Processing {ticker}..."):
            stock_data = finance_service.get_stock_data(ticker)

            if stock_data is None:
                console.print(
                    f"[bold yellow]Warning:[/bold yellow] Could not fetch data for {ticker}, skipping...",
                )
                continue

            result = analyzer.analyze(stock_data)
            results.append((stock_data, result))

    if not results:
        console.print("[bold red]Error:[/bold red] No valid stocks to compare")
        return

    # Display comparison table
    _display_comparison_table(results)


def _display_company_info(stock_data):
    """Display basic company information."""
    info = stock_data.company_info

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Ticker", get_ticker_without_suffix(info.ticker))
    table.add_row("Company", info.name)
    if info.sector:
        table.add_row("Sector", info.sector)
    if info.industry:
        table.add_row("Industry", info.industry)

    panel = Panel(
        table,
        title="[bold]Company Information[/bold]",
        border_style="blue",
    )
    console.print(panel)
    console.print()


def _display_screening_summary(result):
    """Display screening summary with rating and score."""
    # Determine color based on rating
    if result.rating.name == "VERY_STRONG":
        color = "bold green"
    elif result.rating.name == "STRONG":
        color = "green"
    elif result.rating.name == "FAIR":
        color = "yellow"
    elif result.rating.name == "WEAK":
        color = "red"
    else:
        color = "bold red"

    # Create summary text
    summary = Text()
    summary.append("Fundamental Rating: ", style="bold")
    summary.append(str(result.rating), style=color)
    summary.append("\nTotal Score: ", style="bold")
    summary.append(f"{result.metrics.total_score:.1f}/100", style=color)
    summary.append(
        f"\nData Quality: {result.data_completeness:.0f}%",
        style="dim",
    )

    panel = Panel(summary, title="[bold]Screening Result[/bold]", border_style=color)
    console.print(panel)
    console.print()


def _display_category_scores(result):
    """Display scores for each category."""
    table = Table(title="Category Scores", show_header=True)

    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Score", justify="right", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Weight", justify="right", style="dim")

    for cat_score in result.metrics.get_all_category_scores():
        # Determine status icon
        if cat_score.passed:
            status = "[green]✓ Pass[/green]"
        else:
            status = "[red]✗ Fail[/red]"

        # Determine color based on score
        if cat_score.score >= 70:
            score_color = "green"
        elif cat_score.score >= 50:
            score_color = "yellow"
        else:
            score_color = "red"

        table.add_row(
            cat_score.category,
            f"[{score_color}]{cat_score.score:.1f}/100[/{score_color}]",
            status,
            f"{cat_score.weight * 100:.0f}%",
        )

    console.print(table)
    console.print()


def _display_key_metrics(result):
    """Display key financial metrics."""
    metrics = result.key_metrics

    table = Table(title="Key Financial Metrics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="white")

    # Valuation
    if metrics.get("pe_ratio"):
        table.add_row("PE Ratio", format_ratio(metrics["pe_ratio"]))
    if metrics.get("pbv"):
        table.add_row("PBV", format_ratio(metrics["pbv"]))
    if metrics.get("market_cap"):
        table.add_row("Market Cap", format_currency(metrics["market_cap"]))

    # Profitability
    if metrics.get("roe"):
        table.add_row("ROE", format_percentage(metrics["roe"]))
    if metrics.get("gross_margin"):
        table.add_row("Gross Margin", format_percentage(metrics["gross_margin"]))
    if metrics.get("eps"):
        table.add_row("EPS", format_number(metrics["eps"]))

    # Risk
    if metrics.get("debt_to_equity"):
        table.add_row(
            "Debt-to-Equity",
            format_ratio(metrics["debt_to_equity"]),
        )

    # Dividend
    if metrics.get("dividend_yield"):
        table.add_row(
            "Dividend Yield",
            format_percentage(metrics["dividend_yield"]),
        )

    # Price
    if metrics.get("current_price"):
        table.add_row("Current Price", format_currency(metrics["current_price"]))

    console.print(table)
    console.print()


def _display_insights(result):
    """Display insights, strengths, and weaknesses."""
    # Strengths
    if result.strengths:
        console.print("[bold green]Strengths:[/bold green]")
        for strength in result.strengths:
            console.print(f"  [green]✓[/green] {strength}")
        console.print()

    # Weaknesses
    if result.weaknesses:
        console.print("[bold yellow]Weaknesses:[/bold yellow]")
        for weakness in result.weaknesses:
            console.print(f"  [yellow]⚠[/yellow] {weakness}")
        console.print()

    # Red Flags
    if result.red_flags:
        console.print("[bold red]Red Flags:[/bold red]")
        for flag in result.red_flags:
            console.print(f"  [red]✗[/red] {flag}")
        console.print()


def _display_news_summary(news_items, corporate_actions, news_service):
    """Display news and corporate actions summary."""
    if corporate_actions:
        console.print("[bold]Recent Corporate Actions:[/bold]")
        for action in corporate_actions[:5]:
            date_str = (
                action.published_date.strftime("%Y-%m-%d")
                if action.published_date
                else "N/A"
            )
            console.print(f"  [{date_str}] {action.title}")
        console.print()

    if news_items:
        # Analyze news sentiment
        analysis = news_service.analyze_news_impact(news_items)

        console.print("[bold]News Sentiment Analysis:[/bold]")
        console.print(
            f"  Total News: {analysis['total_news']} | "
            f"[green]Positive: {analysis['positive_count']}[/green] | "
            f"[yellow]Neutral: {analysis['neutral_count']}[/yellow] | "
            f"[red]Negative: {analysis['negative_count']}[/red]",
        )
        console.print(
            f"  Overall Sentiment: [{_get_sentiment_color(analysis['overall_sentiment'])}]"
            f"{analysis['overall_sentiment'].upper()}"
            f"[/{_get_sentiment_color(analysis['overall_sentiment'])}]",
        )

        # Display individual news items dengan detail
        console.print("\n[bold]Recent News:[/bold]")
        for i, news in enumerate(news_items[:5], 1):  # Show top 5 news
            sentiment_color = _get_sentiment_color(news.sentiment)
            date_str = (
                news.published_date.strftime("%Y-%m-%d")
                if news.published_date
                else "N/A"
            )

            console.print(
                f"\n[cyan]{i}. [{sentiment_color}]{news.sentiment.upper()}[/{sentiment_color}][/cyan] [dim]({date_str})[/dim]"
            )
            console.print(f"   [bold]{news.title}[/bold]")

            if news.summary:
                # Truncate summary jika terlalu panjang
                summary = (
                    news.summary[:200] + "..."
                    if len(news.summary) > 200
                    else news.summary
                )
                console.print(f"   [dim]{summary}[/dim]")

        console.print()


def _display_recommendation(result):
    """Display final screening summary."""
    if result.is_strong_fundamentals():
        console.print(
            Panel(
                f"[bold green]FUNDAMENTAL RATING: {result.rating}[/bold green]\n\n"
                f"Berdasarkan analisis fundamental, saham ini menunjukkan kualitas yang baik.\n"
                f"Total Score: {result.metrics.total_score:.1f}/100\n\n"
                f"[dim]Disclaimer: Ini bukan rekomendasi investasi. Lakukan riset sendiri dan konsultasi dengan financial advisor.[/dim]",
                title="Screening Summary",
                border_style="green",
            ),
        )
    else:
        console.print(
            Panel(
                f"[bold yellow]FUNDAMENTAL RATING: {result.rating}[/bold yellow]\n\n"
                f"Pertimbangkan untuk review kembali weaknesses dan red flags.\n"
                f"Total Score: {result.metrics.total_score:.1f}/100\n\n"
                f"[dim]Disclaimer: Ini bukan rekomendasi investasi. Lakukan riset sendiri dan konsultasi dengan financial advisor.[/dim]",
                title="Screening Summary",
                border_style="yellow",
            ),
        )


def _display_comparison_table(results):
    """Display comparison table for multiple stocks."""
    table = Table(title="Stock Comparison", show_header=True)

    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Company", style="white")
    table.add_column("Rating", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("PE", justify="right")
    table.add_column("PBV", justify="right")
    table.add_column("ROE", justify="right")
    table.add_column("D/E", justify="right")
    table.add_column("Div Yield", justify="right")

    for stock_data, result in results:
        ticker = get_ticker_without_suffix(stock_data.get_ticker())
        company = stock_data.company_info.name[:20]  # Truncate long names
        rating_str = str(result.rating).split()[0]  # Get first word

        # Get metrics
        pe = format_ratio(result.key_metrics.get("pe_ratio"))
        pbv = format_ratio(result.key_metrics.get("pbv"))
        roe = format_percentage(result.key_metrics.get("roe"))
        de = format_ratio(result.key_metrics.get("debt_to_equity"))
        div_yield = format_percentage(result.key_metrics.get("dividend_yield"))

        # Color code score
        score = result.metrics.total_score
        if score >= 70:
            score_str = f"[green]{score:.1f}[/green]"
        elif score >= 50:
            score_str = f"[yellow]{score:.1f}[/yellow]"
        else:
            score_str = f"[red]{score:.1f}[/red]"

        table.add_row(
            ticker,
            company,
            rating_str,
            score_str,
            pe,
            pbv,
            roe,
            de,
            div_yield,
        )

    console.print(table)


def _get_sentiment_color(sentiment: str) -> str:
    """Get color for sentiment."""
    if sentiment == "positive":
        return "green"
    if sentiment == "negative":
        return "red"
    return "yellow"


@cli.command()
def interactive():
    """Interactive mode - prompt user untuk input.

    Mode ini akan memandu user step-by-step untuk screening saham.
    """
    # Welcome banner
    console.print()
    console.print(
        Panel(
            "[bold cyan]Friday Screener[/bold cyan]\n"
            "Stock Screening Tool untuk Bursa Efek Indonesia\n\n"
            "[dim]Professional-grade fundamental analysis[/dim]",
            border_style="cyan",
        ),
    )
    console.print()

    while True:
        # Ask mode
        console.print("[bold]Pilih Mode:[/bold]")
        console.print("  [cyan]1[/cyan] - Screen single stock")
        console.print("  [cyan]2[/cyan] - Compare multiple stocks")
        console.print("  [cyan]q[/cyan] - Quit")
        console.print()

        mode = (
            console.input(
                "[bold green]Pilihan Anda[/bold green] [dim](default: 1)[/dim]: "
            )
            .strip()
            .lower()
        )

        # Default to 1 if empty
        if not mode:
            mode = "1"

        if mode in ["q", "quit", "exit"]:
            console.print(
                "\n[bold cyan]Terima kasih telah menggunakan Friday Screener! 👋[/bold cyan]\n"
            )
            break

        if mode == "1":
            # Single stock screening
            _interactive_single_screen()
        elif mode == "2":
            # Multiple stock comparison
            _interactive_compare()
        else:
            console.print(
                "[red]❌ Pilihan tidak valid. Silakan pilih 1, 2, atau q[/red]\n"
            )
            continue

        # Ask to continue
        console.print()
        continue_input = (
            console.input(
                "[bold green]Lakukan screening lagi?[/bold green] [dim](Y/n)[/dim]: "
            )
            .strip()
            .lower()
        )

        if continue_input in ["n", "no"]:
            console.print(
                "\n[bold cyan]Terima kasih telah menggunakan Friday Screener! 👋[/bold cyan]\n"
            )
            break
        console.print()


def _interactive_single_screen():
    """Interactive mode untuk single stock screening."""
    console.print()

    # Use Rich console.input for colored prompts
    ticker = (
        console.input(
            "[bold cyan]Masukkan ticker saham[/bold cyan] [dim](contoh: BBCA, TLKM)[/dim]: "
        )
        .strip()
        .upper()
    )

    if not ticker:
        console.print("[red]Ticker tidak boleh kosong![/red]")
        return

    # Options with colored prompts
    console.print()
    detailed_input = (
        console.input(
            "[bold yellow]Tampilkan detailed analysis?[/bold yellow] [dim](y/N)[/dim]: "
        )
        .strip()
        .lower()
    )
    detailed = detailed_input in ["y", "yes"]

    news_input = (
        console.input(
            "[bold yellow]Include news & corporate actions?[/bold yellow] [dim](Y/n)[/dim]: "
        )
        .strip()
        .lower()
    )
    include_news = news_input not in ["n", "no"]

    console.print()

    # Call screen function with context
    ctx = click.get_current_context()
    ctx.invoke(screen, ticker=ticker, detailed=detailed, news=include_news)


def _interactive_compare():
    """Interactive mode untuk comparing stocks."""
    console.print()
    console.print(
        "[dim]Masukkan ticker dipisahkan dengan spasi (contoh: BBCA BMRI BBNI)[/dim]"
    )
    console.print()

    # Use Rich console.input for colored prompts
    tickers_input = (
        console.input("[bold cyan]Masukkan tickers[/bold cyan]: ").strip().upper()
    )

    if not tickers_input:
        console.print("[red]Tickers tidak boleh kosong![/red]")
        return

    # Parse tickers
    tickers = tuple(tickers_input.split())

    if len(tickers) < MIN_COMPARISON_TICKERS:
        console.print("[red]Error: Minimal 2 ticker untuk comparison[/red]")
        return

    console.print()

    # Call compare function with context
    ctx = click.get_current_context()
    ctx.invoke(compare, tickers=tickers)


if __name__ == "__main__":
    cli()
