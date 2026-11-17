"""The full-screen interface asks the same questions and writes the same file (feature 013, US4).

Driven by Textual's pilot, so no terminal is needed. Skipped where the authoring extra is not
installed; CI runs it in its own job with the extra.
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest

pytest.importorskip("textual")

from caravan.cli.main import EXIT_OK, main
from caravan.init.session import Session
from caravan.tui.app import InitApp

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")


async def drive(session: Session, steps) -> InitApp:
    app = InitApp(session)
    async with app.run_test(size=(170, 50)) as pilot:
        await pilot.pause()
        for step in steps:
            await step(app, pilot)
            await pilot.pause()
            await pilot.pause()
    return app


async def type_data(app, pilot) -> None:
    app.query_one("#value").value = SYNTHETIC
    await pilot.press("enter")


async def tick_s32k144(app, pilot) -> None:
    await pilot.press("down", "space", "enter")


def enter(times: int):
    async def press(app, pilot) -> None:
        for _ in range(times):
            if app.session.current().kind == "form":
                await pilot.press("ctrl+s")
            else:
                await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

    return press


def test_accepting_every_proposal_writes_what_no_input_writes(tmp_path, monkeypatch) -> None:
    session = Session({}, cwd=tmp_path)
    app = asyncio.run(drive(session, [type_data, tick_s32k144, enter(11)]))
    assert app.return_value is True and session.done
    target, findings = session.write()
    assert not findings
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    args = ["init", "b.yaml", "--no-input", "--dataset", SYNTHETIC, "--board", "s32k144"]
    assert main(args) == EXIT_OK
    assert target.read_bytes() == (tmp_path / "b.yaml").read_bytes()


def test_adding_a_layer_changes_the_drawing_and_the_memory(tmp_path) -> None:
    session = Session({}, cwd=tmp_path)
    seen: dict[str, str] = {}

    def note(name: str):
        async def keep(app, pilot) -> None:
            seen[name] = "\n".join(line for s in session.explain() for line in s.lines)

        return keep

    async def add_layer(app, pilot) -> None:
        await pilot.click("#add--hidden")

    # quantization, output, output type, inputs, window, template: six Enters to the form.
    steps = [type_data, tick_s32k144, enter(6), note("before"), add_layer, note("after")]
    asyncio.run(drive(session, steps))
    assert session.current().key == "params"
    assert "hidden_3" not in seen["before"] and "hidden_3" in seen["after"]
    assert seen["before"].split("flash ≥")[1][:12] != seen["after"].split("flash ≥")[1][:12]


def test_escape_goes_back_and_keeps_the_answer(tmp_path) -> None:
    session = Session({}, cwd=tmp_path)

    async def back(app, pilot) -> None:
        await pilot.press("escape")

    asyncio.run(drive(session, [type_data, tick_s32k144, enter(1), back, back]))
    assert session.current().key == "boards"
    assert session.answers["boards"] == ["s32k144"]
    assert session.answers["quantization"] == "int8"


def test_quit_writes_nothing(tmp_path) -> None:
    session = Session({}, cwd=tmp_path)

    async def leave(app, pilot) -> None:
        await pilot.press("ctrl+q")

    app = asyncio.run(drive(session, [type_data, leave]))
    assert app.return_value is False
    assert not list(tmp_path.iterdir())
