
import sys
import os
import asyncio
from datetime import datetime

# Add current directory to sys.path so we can import backend
sys.path.append(os.getcwd())

try:
    from backend.user_state_manager import set_manual_period_date, get_manual_period_date
    from backend.api import confirm_period
except ImportError as e:
    print(f"Import Error: {e}")
    # try adjusting path if backend is not found
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    try:
        from user_state_manager import set_manual_period_date, get_manual_period_date
        # We can't easily import api if it depends on relative imports and we are messing with path
        # But let's try the first approach which matches how uvicorn runs
    except ImportError as e2:
        print(f"Import Error 2: {e2}")
        sys.exit(1)

async def test_logic():
    print("Testing set_manual_period_date directly...")
    try:
        date_obj = datetime.now().date()
        set_manual_period_date(date_obj)
        print("Success: set_manual_period_date")
    except Exception as e:
        print(f"FAIL: set_manual_period_date raised {e}")

    print("\nTesting confirm_period endpoint logic...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        # replicate what FastAPI passes: simple string from Form
        # But wait, confirm_period is an async function.
        # It takes date: str = Form(...)
        # We can call it directly with the string.
        response = await confirm_period(date=date_str)
        print(f"Success: confirm_period returned {response}")
    except Exception as e:
        print(f"FAIL: confirm_period raised {e}")

if __name__ == "__main__":
    asyncio.run(test_logic())
