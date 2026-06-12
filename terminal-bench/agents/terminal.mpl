// Terminal-Bench agent as an MPL cage.
//
// The chart owns control flow: a perceive -> think -> act loop, a step budget,
// and termination. The host (mpl_agent.py) provides the three side-effecting
// leaves as `host import`s:
//
//   observe()        -> the current terminal screen
//   decide(obs)      -> the next shell command, or the sentinel "__DONE__"
//                       when the brain judges the task complete
//   act(command)     -> sends the command into the container, returns new screen
//
// MPL's next-tick semantics matter here: a var written in a `then { }` block is
// only readable on the FOLLOWING tick. So each side-effecting host call fires
// exactly once on a transition, and the branch logic reads only committed vars.
// One loop iteration spans three ticks: Perceive, Think, Act.

host import {
    observe() -> string,
    decide(obs:string) -> string,
    act(command:string) -> string,
} from agent;

default machine Agent {
    vars {
        obs:string := "";
        cmd:string := "";
        last_screen:string := "";
        steps:int := 0;
        max_steps:int := 12;
        finished:bool := false;
    }

    state Perceive;
    state Think;
    state Act;
    state Done;
    ENTER => Perceive;

    // Perceive: snapshot the terminal, then advance to Think.
    Perceive => Think then { obs := observe(); };

    // Think: consult the brain exactly once; stash its command, count the step.
    Think => Act then { cmd := decide(obs); steps += 1; };

    // Act: the cage's termination + budget guards, branching on committed vars.
    // The brain said done:
    Act when cmd == "__DONE__" => Done then { finished := true; };
    // Out of budget:
    Act when cmd != "__DONE__" && steps >= max_steps => Done then { finished := true; };
    // Otherwise execute the command (one act() call) and loop back to Perceive:
    Act when cmd != "__DONE__" && steps < max_steps => Perceive then { last_screen := act(cmd); };

    // Done is terminal: no outgoing rules. `finished` latches for the host watcher.
}
