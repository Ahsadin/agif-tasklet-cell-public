use std::io::{self, Read};

fn main() {
    let mut input = String::new();
    if io::stdin().read_to_string(&mut input).is_err() {
        eprintln!("stdin_read_failed");
        std::process::exit(2);
    }

    match agif_wasm_inference_v6::run_from_json(&input) {
        Ok(output) => {
            println!("{output}");
        }
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(3);
        }
    }
}
