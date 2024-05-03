# `twf`

**Usage**:

```console
$ twf [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `task`: Run taskwarrior with the given data group
* `utils`: Sub-commands for taskwarrior utilities

## `twf task`

Run taskwarrior with the given data group

**Usage**:

```console
$ twf task [OPTIONS]
```

**Options**:

* `-g, --group TEXT`: [default: default]
* `--help`: Show this message and exit.

## `twf utils`

Sub-commands for taskwarrior utilities

**Usage**:

```console
$ twf utils [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `add`: Add task, query, and template
* `edit`: Edit query, and template
* `view`: View task and template

### `twf utils add`

Add task, query, and template

**Usage**:

```console
$ twf utils add [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: [default: task]

**Options**:

* `-g, --group TEXT`: [default: default]
* `--help`: Show this message and exit.

### `twf utils edit`

Edit query, and template

**Usage**:

```console
$ twf utils edit [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: [default: template]

**Options**:

* `--help`: Show this message and exit.

### `twf utils view`

View task and template

**Usage**:

```console
$ twf utils view [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: [default: task]

**Options**:

* `--help`: Show this message and exit.
