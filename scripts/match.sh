#!/bin/bash

echo "Partida entre $3$4 e $4$3..."
./scripts/player2 $1 $2 $3$4 > /dev/null &
./scripts/player1 $1 $2 $4$3 $3$4 > /dev/null &
wait
