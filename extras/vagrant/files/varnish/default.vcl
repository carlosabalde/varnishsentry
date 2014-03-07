import std;

backend default {
    .host = "127.0.0.1";
    .port = "8080";
}

sub vcl_recv {
    if (std.random(0, 100) < 50) {
        std.log("[WTF] We have just flipped a coin and it has landed on the bad side!");
    }
}
