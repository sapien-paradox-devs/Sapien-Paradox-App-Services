---
name: create-machine
description: Scaffold a new XState v5 state machine with the project's folder convention. Use when user asks to create a new machine, state machine, or feature that needs one.
---

Create a new XState v5 state machine following the project's established pattern. The user will provide the machine name, states, events, and context.

## Folder Structure

Each machine lives in its own folder under `frontend/src/`:

```
<name>/machine/
  machine.ts    — createMachine only, string references for actions/actors/guards
  actions.ts    — individual const using assign, collected into one exported object
  actors.ts     — individual const using fromPromise, collected into one exported object
  guards.ts     — individual named exports, imported via `import * as guards`
  index.ts      — machine.provide({ actions, actors, guards })
```

## File Templates

### machine.ts
- Import only `createMachine` from `"xstate"`
- Define context as a plain object literal, no type annotations
- Reference actions, actors, guards by string name only — no implementations here
- Actors go in `invoke: { src: "actorName" }` with `onDone`/`onError`

```ts
import { createMachine } from "xstate";

export const someMachine = createMachine({
  id: "some",
  initial: "idle",
  context: {
    data: null,
    error: null,
  },
  states: {
    idle: {
      on: { FETCH: "loading" },
    },
    loading: {
      invoke: {
        src: "fetchData",
        onDone: { target: "ready", actions: "setData" },
        onError: { target: "idle", actions: "setError" },
      },
    },
    ready: {},
  },
});
```

### actions.ts
- Each action is a standalone `const` using `assign(({ context, event }) => { return {...} })`
- No type annotations on parameters — just `({ context, event })` or `({ event })` or `()`
- Collected into a single named export `export const actions = { ... }`

```ts
import { assign } from "xstate";

const setData = assign(({ event }) => {
  return { data: event.output, error: null };
});

const setError = assign(({ event }) => {
  const message = event.error instanceof Error ? event.error.message : "Something went wrong";
  return { error: message };
});

export const actions = {
  setData,
  setError,
};
```

### actors.ts
- Each actor is a `fromPromise(async () => ...)` that calls `mappedFetcher.get(...)` or `mappedFetcher.post(...)`
- No generic type params on fetcher calls — just `mappedFetcher.get("/path")`
- Collected into a single named export `export const actors = { ... }`

```ts
import { fromPromise } from "xstate";
import { mappedFetcher } from "../lib/fetcher";

export const actors = {
  fetchData: fromPromise(async () => {
    return mappedFetcher.get("/some/endpoint");
  }),
};
```

### guards.ts
- Each guard is an individual named export: `export const guardName = ({ context }) => { ... }`
- No wrapper object — just bare exports

```ts
export const hasData = ({ context }) => {
  return context.data !== null;
};

export const hasError = ({ context }) => {
  return context.error !== null;
};
```

### index.ts
- Imports machine, actions, actors as named imports
- Imports guards via `import * as guards`
- Exports the provided machine

```ts
import { someMachine } from "./machine";
import { actions } from "./actions";
import { actors } from "./actors";
import * as guards from "./guards";

export const machine = someMachine.provide({
  actions,
  actors,
  guards,
});
```

## Component Usage

Components consume the machine via `useMachine`:

```tsx
import { useMachine } from "@xstate/react";
import { machine } from "./machine";

function SomeComponent() {
  const [state, send] = useMachine(machine);

  // Use state.matches("stateName") for conditional rendering
  // Use state.context.field for data
  // Use send({ type: "EVENT_NAME" }) to trigger transitions
}
```

## Rules

- Keep it simple — no `satisfies`, no explicit generics, no wrapper types
- Machine file is purely declarative — all logic lives in actions/actors/guards
- Actions use `assign` returning a plain object to merge into context
- Actors use `fromPromise` calling `mappedFetcher`
- Guards are plain functions returning boolean
- Events are `{ type: "UPPER_SNAKE_CASE" }`
