# test/test_decision_logic.py
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestrator_agent import _ask_vlm_needs_screenshot, console

def test_decision():
    console.print("[bold]Testing VLM Decision Logic[/bold]\n")
    
    # Scenario 1: Request for visual (New Screenshot)
    query1 = "What is on my screen right now?"
    context1 = ""
    console.print(f"[cyan]Query:[/cyan] {query1}")
    decision1 = _ask_vlm_needs_screenshot(query1, context1)
    console.print(f"[yellow]Result:[/yellow] {decision1}\n")
    
    # Scenario 2: General question (None)
    query2 = "Who is the president of France?"
    context2 = ""
    console.print(f"[cyan]Query:[/cyan] {query2}")
    decision2 = _ask_vlm_needs_screenshot(query2, context2)
    console.print(f"[yellow]Result:[/yellow] {decision2}\n")
    
    # Scenario 3: Reference to past image (Use Past Image)
    # Create fake history where index 1 (older) has an image
    query3 = "What was the color of the car in that picture?"
    context3 = """[2023-10-27 10:00:00] User: Look at this car [Image Available (index 1)]
[2023-10-27 10:00:05] Agent: It's a nice red sports car.
[2023-10-27 10:00:10] User: Okay thanks."""
    
    console.print(f"[cyan]Query:[/cyan] {query3}")
    console.print(f"[dim]Context:[/dim]\n{context3}")
    decision3 = _ask_vlm_needs_screenshot(query3, context3)
    console.print(f"[yellow]Result:[/yellow] {decision3}\n")

if __name__ == "__main__":
    test_decision()
