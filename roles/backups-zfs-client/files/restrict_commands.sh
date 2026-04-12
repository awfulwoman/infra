#!/bin/bash
export PATH=/usr/sbin:$PATH

_RE_DATASET=$'[\"\']+[a-z0-9/_]+[\"\']+'
_RE_SNAPSHOT=$'[\"\']+[a-z0-9/_]+[\"\']*@[\"\']*[a-z0-9/_:-]+[\"\']+'
_RE_SIZE=$'[0-9]+[kMG]?'

_WHITELIST=(
   -e "exit"
   -e "echo -n"
   -e "zpool get -o value -H feature@extensible_dataset $_RE_DATASET"
   -e "zfs get -H syncoid:sync $_RE_DATASET"
   -e "zfs get -Hpd 1 -t snapshot guid,creation $_RE_DATASET"
   -e " *zfs send -R -w -nv?P $_RE_SNAPSHOT"
   -e " *zfs send -R -w +$_RE_SNAPSHOT \| +lzop *(\| mbuffer +-q -s $_RE_SIZE -m $_RE_SIZE 2>/dev/null)?"
   -e " *zfs send -R -w -nv?P +-I $_RE_SNAPSHOT $_RE_SNAPSHOT"
   -e " *zfs send -R -w +-I $_RE_SNAPSHOT $_RE_SNAPSHOT \| lzop *(\| mbuffer +-q -s $_RE_SIZE -m $_RE_SIZE 2>/dev/null)?"
   -e "command -v (lzop|mbuffer)"
)

## LOG non-whitelisted commands, execute whitelisted
echo "$SSH_ORIGINAL_COMMAND" |\
tee >(egrep -x -v "${_WHITELIST[@]}" \
    | ts "non-whitelisted command issued: (client $SSH_CLIENT)" \
    | logger -p local0.crit \
) |\
egrep -x "${_WHITELIST[@]}" | bash
