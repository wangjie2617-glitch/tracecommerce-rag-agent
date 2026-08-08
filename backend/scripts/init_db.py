"""Create local development tables without replacing production Alembic usage."""

from __future__ import annotations

import asyncio

from app.db.session import create_all_for_development


async def main() -> None:
    await create_all_for_development()
    print("数据库表已创建。生产环境请优先执行 alembic upgrade head。")


if __name__ == "__main__":
    asyncio.run(main())

