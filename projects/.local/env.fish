if not contains "$HOME/Documents/New project 2/.local" $PATH
    # Prepending path in case a system-installed binary needs to be overridden
    set -x PATH "$HOME/Documents/New project 2/.local" $PATH
end
