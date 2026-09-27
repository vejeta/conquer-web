# shellcheck shell=bash
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Texts of the player menu and the join wizard in the player's language,
# sourced by both (installed as /usr/local/lib/conquer-i18n.sh). The texts
# are in /usr/local/share/conquer-web/i18n/<language>.sh (conquer/i18n in
# the repository); English is loaded first, so a text a language does not
# have is shown in English. Needs the styles (bold, dim, yellow, green,
# reset) defined before load_texts.

I18N_DIR="${CONQUER_I18N_DIR:-/usr/local/share/conquer-web/i18n}"
declare -gA MSG=()

# load_texts CODE: CODE comes from the browser (/play/?arg=CODE), so it is
# used only when it is a language code with texts of its own
load_texts() {
    # shellcheck source=../i18n/en.sh
    . "$I18N_DIR/en.sh"
    if [[ "${1:-}" =~ ^[a-z]{2,3}(-[a-z]{2,4})?$ ]] && [ "$1" != en ] && [ -f "$I18N_DIR/$1.sh" ]; then
        # shellcheck source=/dev/null
        . "$I18N_DIR/$1.sh"
    fi
}

# t KEY [VALUE...]: the text KEY, with its %s filled in by the values
t() {
    local format="${MSG[$1]:-$1}"
    shift
    # shellcheck disable=SC2059 # the catalogs are formats
    printf -- "$format" "$@"
}

# tr_raw KEY: the text as is (for texts that are not printf formats)
tr_raw() {
    printf '%s' "${MSG[$1]:-}"
}
