import asyncio
from datetime import datetime
import logging
import logging.config

from docker_secrets import getDocketSecrets
from ideenergy import get_session, RequestFailedError, Client
import pandas as pd


logger = logging.getLogger(__name__)


async def get_contract_data(client: Client) -> tuple[str, str]:
    contracts = await client.get_contracts()
    cups = contracts[0]["cups"]
    direccion = contracts[0]["direccion"]
    return cups, direccion


async def _get_energy_consumption(
    start: datetime, end: datetime, username: str = "", password: str = ""
):

    if not username:
        username = getDocketSecrets("username")
    if not password:
        password = getDocketSecrets("password")

    session = await get_session()
    client = Client(
        username=username,
        password=password,
        session=session,
        logger=logger,
    )

    try:
        consumption: pd.DataFrame = await client.get_historical_consumption_pd(
            start, end
        )
        return consumption

    except RequestFailedError:
        logger.error("Request failed.", exc_info=True)
    finally:
        await session.close()

    return pd.DataFrame()


def get_energy_consumption(start: datetime, end: datetime):
    return asyncio.run(_get_energy_consumption(start, end))
