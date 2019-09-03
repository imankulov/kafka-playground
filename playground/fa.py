"""
Faust playground.
"""
import faust

app = faust.App(
    "myapp", broker="kafka://kafka1", value_serializer="raw", store="memory://"
)
tiny = app.topic("tiny")


@app.agent(tiny)
async def process_message(messages):
    async for message in messages:
        print(message)


# @app.timer(interval=10)
# async def ping():
#    print("ping")
