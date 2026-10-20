"""The three lifecycles, driven whole without a guest: the session's phases, the guest's
soundness and the home's phases, each a table one function moves along. Every row of each table
is driven on a bare state; every pair the table does not hold is refused with a `RuntimeError`
naming both; no member is dead. The frozen checked call has its one row here too."""

from __future__ import annotations

import dataclasses
import itertools
import threading
from typing import Any

import pytest

from harness import calls
from wasi_python import _call, _engines, _home, _sessions
from wasi_python._home import _HomeEvent as HE
from wasi_python._home import _HomePhase as HP
from wasi_python._sessions import _CLOSER
from wasi_python._sessions import _Event as E
from wasi_python._sessions import _Guest as G
from wasi_python._sessions import _GuestEvent as GE
from wasi_python._sessions import _Phase as P

# --- the checked call -------------------------------------------------------------------------


def test_a_checked_call_is_frozen_with_every_field_required() -> None:
    """Nineteen fields, each required: a construction that leaves one out is a `TypeError` at
    the construction; a write after it is refused; the stand-in's copy refuses an unknown name."""
    names = [f.name for f in dataclasses.fields(_call._CheckedCall)]
    assert len(names) == 19 and all(
        f.default is dataclasses.MISSING for f in dataclasses.fields(_call._CheckedCall)
    )
    given = {name: getattr(calls.BASE_CALL, name) for name in names}
    assert _call._CheckedCall(**given) == calls.BASE_CALL
    for name in names:
        with pytest.raises(TypeError, match=name):
            _call._CheckedCall(**{k: v for k, v in given.items() if k != name})
    with pytest.raises(dataclasses.FrozenInstanceError):
        calls.BASE_CALL.fuel = 1  # type: ignore[misc]
    with pytest.raises(TypeError, match="home"):
        calls.checked_call(home=object())
    assert calls.checked_call(fuel=7).fuel == 7 and calls.BASE_CALL.fuel is None


# --- the session's table ----------------------------------------------------------------------


def _state() -> _sessions._State:
    return _sessions._State(calls.BASE_CALL, _engines._wasmtime())


def _at(phase: P, holder: int | None = None) -> _sessions._State:
    """A bare state placed in `phase`, its wait handles as the invariants say."""
    s = _state()
    s.phase, s.holder = phase, holder
    if phase in (P.STOPPING, P.MARKED, P.ENDING, P.ENDED):
        s.ended = "closed"
        s.closing.set()
    if phase is P.ENDED:
        s.done.set()
    return s


ME = 12345

# (phase, holder before, event, holder given, phase after, holder after, closing, done)
SESSION_ROWS = [
    (P.OPENING, None, E.OPENED, None, P.OPEN, None, False, False),
    (P.OPENING, None, E.RELEASED, None, P.ENDED, None, False, True),
    (P.OPEN, None, E.CLAIM, ME, P.TURN, ME, False, False),
    (P.OPEN, None, E.MARK, None, P.MARKED, None, True, False),
    (P.TURN, ME, E.RELEASE, None, P.OPEN, None, False, False),
    (P.TURN, ME, E.MARK, None, P.STOPPING, ME, True, False),
    (P.TURN, ME, E.TURN_RETURNED, None, P.OPEN, None, False, False),
    (P.STOPPING, ME, E.RELEASE, None, P.MARKED, None, True, False),
    (P.STOPPING, ME, E.TURN_RETURNED, None, P.MARKED, None, True, False),
    (P.MARKED, None, E.CLAIM_ENDING, ME, P.ENDING, ME, True, False),
    (P.MARKED, None, E.CLAIM_ENDING, _CLOSER, P.ENDING, _CLOSER, True, False),
    (P.ENDING, _CLOSER, E.TAKE_OVER, ME, P.ENDING, ME, True, False),
    (P.ENDING, ME, E.RELEASED, None, P.ENDED, None, True, True),
]
SESSION_PAIRS = {(before, event) for before, _, event, *_ in SESSION_ROWS}


@pytest.mark.parametrize("row", SESSION_ROWS, ids=lambda r: f"{r[0].name}-{r[2].name}")
def test_the_session_table_row(row) -> None:
    before, holder, event, given, after, holder_after, closing, done = row
    s = _at(before, holder)
    assert _sessions._move(s, event, given) is after
    assert (s.phase, s.holder) == (after, holder_after)
    assert (s.closing.is_set(), s.done.is_set()) == (closing, done)


def test_the_session_table_is_exhaustive() -> None:
    """Every (phase, event) pair is a row or is refused with a `RuntimeError` naming both, and
    every member of either enum has a row, so a member added without its rows is red here."""
    assert {r[0] for r in SESSION_ROWS} | {r[4] for r in SESSION_ROWS} == set(P)
    assert {r[2] for r in SESSION_ROWS} == set(E)
    for phase, event in itertools.product(P, E):
        s = _at(phase, ME)
        if (phase, event) in SESSION_PAIRS:
            _sessions._move(s, event, ME)
            continue
        with pytest.raises(RuntimeError, match=rf"{phase.name}.*{event.name}"):
            _sessions._move(s, event, ME)
        assert s.phase is phase, "a refused pair moved the phase"


def test_the_session_table_is_live() -> None:
    """Every member but the initial one is reached by some row; every member but the terminal
    one leaves by some row."""
    targets = {r[4] for r in SESSION_ROWS}
    sources = {r[0] for r in SESSION_ROWS}
    assert targets == set(P) - {P.OPENING}
    assert sources == set(P) - {P.ENDED}
    assert {r[2] for r in SESSION_ROWS} == set(E)


def test_the_two_session_pairs_the_flags_allowed_are_refused() -> None:
    """A claim of the ending on a state whose `ended` is None, and a move from OPENING by
    anything but OPENED or RELEASED: today's flags let both through; no path reaches them."""
    for phase in (P.OPEN, P.TURN, P.STOPPING):
        s = _at(phase, ME if phase is not P.OPEN else None)
        with pytest.raises(RuntimeError, match=rf"{phase.name}.*CLAIM_ENDING"):
            _sessions._claim_ending(s, ME)
    for event in set(E) - {E.OPENED, E.RELEASED}:
        with pytest.raises(RuntimeError, match=rf"OPENING.*{event.name}"):
            _sessions._move(_state(), event, ME)


def test_the_claim_of_an_ending_says_who_has_it() -> None:
    """`_claim_ending` is False, with no event, once someone holds the ending or it is over."""
    s = _at(P.MARKED)
    assert _sessions._claim_ending(s, ME) is True and (s.phase, s.holder) == (P.ENDING, ME)
    assert _sessions._claim_ending(s, 99) is False and (s.phase, s.holder) == (P.ENDING, ME)
    assert _sessions._claim_ending(_at(P.ENDED), ME) is False


def test_a_mark_is_the_one_writer_of_ended() -> None:
    """`_mark` moves OPEN to MARKED or TURN to STOPPING and says True; a second mark says False
    and raises no event."""
    s = _at(P.OPEN)
    assert _sessions._mark(s, "idle") is True and (s.phase, s.ended) == (P.MARKED, "idle")
    assert s.closing.is_set()
    assert _sessions._mark(s, "closed") is False and (s.phase, s.ended) == (P.MARKED, "idle")
    t = _at(P.TURN, ME)
    assert _sessions._mark(t, "closed") is True and (t.phase, t.holder) == (P.STOPPING, ME)


def test_the_release_counts_down_only_from_an_ending() -> None:
    """The open-session count is decremented by a release in ENDING and never by one in OPENING,
    the failed opening."""
    from wasi_python._process import process

    p = process()
    with p.cache_lock:
        before = p.counts["sessions_open"]
    _sessions._release_session(_at(P.ENDING, ME))
    with p.cache_lock:
        assert p.counts["sessions_open"] == before - 1
        p.counts["sessions_open"] = before
    _sessions._release_session(_state())
    with p.cache_lock:
        assert p.counts["sessions_open"] == before


# --- the guest's table ------------------------------------------------------------------------

GUEST_ROWS = [
    (G.UNTOUCHED, GE.ENTER, G.ENTERED),
    (G.SOUND, GE.ENTER, G.ENTERED),
    (G.ENTERED, GE.RETURNED, G.SOUND),
    (G.ENTERED, GE.UNWOUND, G.UNSOUND),
    (G.UNTOUCHED, GE.FAILED, G.UNSOUND),
    (G.ENTERED, GE.FAILED, G.UNSOUND),
    (G.SOUND, GE.FAILED, G.UNSOUND),
]
GUEST_PAIRS = {(before, event) for before, event, _ in GUEST_ROWS}


@pytest.mark.parametrize("row", GUEST_ROWS, ids=lambda r: f"{r[0].name}-{r[1].name}")
def test_the_guest_table_row(row) -> None:
    before, event, after = row
    s = _state()
    s.guest = before
    assert _sessions._move_guest(s, event) is after and s.guest is after


def test_the_guest_table_is_exhaustive() -> None:
    assert {r[0] for r in GUEST_ROWS} | {r[2] for r in GUEST_ROWS} == set(G)
    assert {r[1] for r in GUEST_ROWS} == set(GE)
    for guest, event in itertools.product(G, GE):
        s = _state()
        s.guest = guest
        if (guest, event) in GUEST_PAIRS:
            _sessions._move_guest(s, event)
            continue
        with pytest.raises(RuntimeError, match=rf"{guest.name}.*{event.name}"):
            _sessions._move_guest(s, event)
        assert s.guest is guest


def test_the_guest_table_is_live() -> None:
    assert {after for *_, after in GUEST_ROWS} == set(G) - {G.UNTOUCHED}
    assert {before for before, *_ in GUEST_ROWS} == set(G) - {G.UNSOUND}
    assert {event for _, event, _ in GUEST_ROWS} == set(GE)


def test_the_shutdown_applies_to_a_sound_guest_only() -> None:
    """Python's shutdown runs only when the last export returned, in a session with a budget, a
    store and no fork; an unsound, an entered or an untouched guest skips it."""
    s = _at(P.ENDING, ME)
    s.shutdown_s, s.store = 5.0, object()
    for guest, applies in (
        (G.SOUND, True),
        (G.UNSOUND, False),
        (G.ENTERED, False),
        (G.UNTOUCHED, False),
    ):
        s.guest = guest
        assert _sessions._shutdown_applies(s) is applies, guest
    s.guest, s.shutdown_s = G.SOUND, 0.0
    assert _sessions._shutdown_applies(s) is False


# --- the home's table -------------------------------------------------------------------------

HOME_ROWS = [
    (HP.IDLE, HE.START, HP.STARTING),
    (HP.DONE, HE.START, HP.STARTING),
    (HP.STARTING, HE.TAKE, HP.RUNNING),
    (HP.STARTING, HE.CANCEL, HP.CANCELLED),
    (HP.STARTING, HE.LEAVE, HP.ABANDONED),
    (HP.RUNNING, HE.LEAVE, HP.ABANDONED),
    (HP.ABANDONED, HE.TAKE, HP.ABANDONED),
    (HP.ABANDONED, HE.LEAVE, HP.ABANDONED),
    (HP.CANCELLED, HE.TAKE, HP.CANCELLED),
    (HP.RUNNING, HE.END, HP.DONE),
    (HP.ABANDONED, HE.END, HP.DONE),
    (HP.RUNNING, HE.LOST, HP.DONE),
    (HP.ABANDONED, HE.LOST, HP.DONE),
]
HOME_PAIRS = {(before, event) for before, event, _ in HOME_ROWS}
HOME_DONE = {HP.IDLE, HP.CANCELLED, HP.DONE}


@pytest.mark.parametrize("row", HOME_ROWS, ids=lambda r: f"{r[0].name}-{r[1].name}")
def test_the_home_table_row(row) -> None:
    before, event, after = row
    home = _home._Home()
    home.phase = before
    assert home._move(event) is after and home.phase is after
    assert home.done is (after in HOME_DONE)


def test_the_home_table_is_exhaustive() -> None:
    assert {r[0] for r in HOME_ROWS} | {r[2] for r in HOME_ROWS} == set(HP)
    assert {r[1] for r in HOME_ROWS} == set(HE)
    for phase, event in itertools.product(HP, HE):
        home = _home._Home()
        home.phase = phase
        if (phase, event) in HOME_PAIRS:
            home._move(event)
            continue
        with pytest.raises(RuntimeError, match=rf"{phase.name}.*{event.name}"):
            home._move(event)
        assert home.phase is phase


def test_the_home_table_is_live() -> None:
    assert {after for *_, after in HOME_ROWS} == set(HP) - {HP.IDLE}
    assert {before for before, *_ in HOME_ROWS} >= set(HP) - {HP.CANCELLED}
    assert {event for _, event, _ in HOME_ROWS} == set(HE)


def test_a_cancelled_home_never_starts_again(monkeypatch) -> None:
    """START from CANCELLED is refused: a late body of the cancelled start could otherwise take
    the new start as its own. The refusal comes before any thread is made."""
    home = _home._Home()
    home.phase = HP.CANCELLED
    started: list[Any] = []
    monkeypatch.setattr(threading.Thread, "start", lambda self: started.append(self))
    with pytest.raises(RuntimeError, match="CANCELLED.*START"):
        _home._start_guest(home, "run", lambda: None, ())
    assert started == [] and home.phase is HP.CANCELLED


def test_a_home_is_left_only_while_a_guest_thread_may_run() -> None:
    """`finish(step)` leaves the step to the guest thread, and stops the guest, in STARTING,
    RUNNING and ABANDONED; in IDLE, CANCELLED and DONE it runs the step at once."""
    ran: list[HP] = []
    for phase in (HP.STARTING, HP.RUNNING, HP.ABANDONED):
        home = _home._Home()
        home.phase = phase
        assert home.finish(lambda: ran.append(phase)) is False  # noqa: B023 (read at once)
        assert (home.phase, ran, len(home.steps)) == (HP.ABANDONED, [], 1)
        assert isinstance(home.raised, _home._Stopped)
    for phase in sorted(HOME_DONE, key=lambda p: p.name):
        home = _home._Home()
        home.phase = phase
        assert home.finish(lambda: ran.append(phase)) is True  # noqa: B023 (read at once)
        assert (home.phase, ran[-1], home.steps, home.raised) == (phase, phase, [], None)
    assert ran == sorted(HOME_DONE, key=lambda p: p.name)


def test_the_join_backstop_cancels_a_start_and_loses_a_run() -> None:
    """A dead thread whose body never reported: the join cancels a start the body never took, and
    writes LOST on a running or abandoned home; a body that moved to DONE and died before its
    last line is left there; in every case `ended` is set, the join returns and nothing runs."""
    for phase, after in (
        (HP.STARTING, HP.CANCELLED),
        (HP.RUNNING, HP.DONE),
        (HP.ABANDONED, HP.DONE),
        (HP.DONE, HP.DONE),
    ):
        home = _home._Home()
        never = threading.Thread(target=lambda: None)  # made, never started
        with home.lock:
            home.phase, home.thread = phase, never
            home.ended.clear()
        _home._join_guest(home)
        assert (home.phase, home.done, home.ended.is_set()) == (after, True, True), phase


def test_a_body_that_starts_after_its_cancel_returns_at_once() -> None:
    home = _home._Home()
    home.phase = HP.CANCELLED
    ran: list[int] = []
    home.body("run", lambda: ran.append(1), ())
    assert ran == [] and home.phase is HP.CANCELLED and home.inbox.empty()
