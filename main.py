import asyncio
import sql_def
import handlers

async def main():
    # Запускаем создание таблицы базы данных
    await sql_def.create_table()
    # Запуск процесса поллинга новых апдейтов
    await handlers.dp.start_polling(handlers.bot)

if __name__ == "__main__":
    asyncio.run(main())