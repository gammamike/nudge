//! Literal Bash arguments only: quotes/escapes, but no expansion or operators.

pub(crate) fn parse(line: &str) -> Option<Vec<String>> {
    if line.is_empty() || line.starts_with(char::is_whitespace) || line.len() > 16_384 {
        return None;
    }
    let mut chars = line.chars().peekable();
    let mut words = Vec::new();
    let mut word = String::new();
    let mut active = false;
    let mut quote = None;
    while let Some(c) = chars.next() {
        if c.is_control() && !(c == '\t' && quote.is_none()) {
            return None;
        }
        match quote {
            Some('\'') => {
                if c == '\'' {
                    quote = None;
                } else {
                    word.push(c);
                }
            }
            Some('"') => match c {
                '"' => quote = None,
                '$' | '`' => return None,
                '\\' => {
                    let next = chars.next()?;
                    if next.is_control() {
                        return None;
                    }
                    if !matches!(next, '$' | '`' | '"' | '\\') {
                        word.push('\\');
                    }
                    word.push(next);
                }
                _ => word.push(c),
            },
            None => match c {
                ' ' | '\t' => {
                    if active {
                        words.push(std::mem::take(&mut word));
                        active = false;
                    }
                }
                '\'' | '"' => {
                    quote = Some(c);
                    active = true;
                }
                '\\' => {
                    let next = chars.next()?;
                    if next.is_control() {
                        return None;
                    }
                    word.push(next);
                    active = true;
                }
                '$' | '`' | ';' | '|' | '&' | '<' | '>' | '(' | ')' | '*' | '?' | '[' | ']'
                | '{' | '}' | '~' | '!' => return None,
                '#' if !active => return None,
                _ => {
                    word.push(c);
                    active = true;
                }
            },
            _ => unreachable!(),
        }
    }
    if quote.is_some() {
        return None;
    }
    if active {
        words.push(word);
    }
    (words.len() >= 2 && words.len() <= 128).then_some(words)
}

pub(crate) fn display(words: &[String]) -> String {
    words
        .iter()
        .map(|word| {
            if !word.is_empty()
                && word
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b"_@%+=:,./-".contains(&b))
            {
                word.clone()
            } else {
                format!("'{}'", word.replace('\'', "'\\''"))
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::{display, parse};

    #[test]
    fn literal_arguments_round_trip() {
        let words = parse("git add -- 'a b' \"x\\qy\" '$(touch nope)' '' a\\ b 'a'\\''b'").unwrap();
        assert_eq!(
            &words[3..],
            ["a b", "x\\qy", "$(touch nope)", "", "a b", "a'b"]
        );
        assert_eq!(parse(&display(&words)).unwrap(), words);
    }

    #[test]
    fn expansions_and_operators_decline() {
        for input in [
            "git add $FILE",
            "git add \"$FILE\"",
            "git add *.rs",
            "git add ~/x",
            "git status; id",
            "git status | cat",
            "git status\n",
            "git add 'broken",
            "git add $(id)",
            "git add <(id)",
            "git add $'x'",
            "git add {a,b}",
            "nix build # comment",
        ] {
            assert!(parse(input).is_none(), "{input}");
        }
    }

    #[test]
    fn hash_inside_a_word_is_literal() {
        let words = parse("nix build nixpkgs#hello .#app").unwrap();
        assert_eq!(&words[2..], ["nixpkgs#hello", ".#app"]);
        assert_eq!(parse(&display(&words)).unwrap(), words);
    }
}
