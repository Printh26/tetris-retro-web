const canvas = document.getElementById("tetris");
const ctx = canvas.getContext("2d");


const COLS = 10;
const ROWS = 20;
const SIZE = 30;


let board;
let piece;
let score = 0;
let lines = 0;
let level = 1;
let gameOver = false;
let paused = false;


const colors = {

I:"#00eaff",
J:"#0066ff",
L:"#ff8800",
O:"#ffe600",
S:"#00ff66",
T:"#bb00ff",
Z:"#ff3355"

};



const shapes = {


I:[
[1,1,1,1]
],


J:[
[1,0,0],
[1,1,1]
],


L:[
[0,0,1],
[1,1,1]
],


O:[
[1,1],
[1,1]
],


S:[
[0,1,1],
[1,1,0]
],


T:[
[0,1,0],
[1,1,1]
],


Z:[
[1,1,0],
[0,1,1]
]


};



function createBoard(){

return Array.from(
{length:ROWS},
()=>Array(COLS).fill(null)
);

}



function randomPiece(){


let keys = Object.keys(shapes);

let type = keys[
Math.floor(Math.random()*keys.length)
];


return {

type:type,

shape:shapes[type],

x:3,

y:0

};


}



function drawCell(x,y,color){


ctx.fillStyle=color;


ctx.fillRect(
x*SIZE,
y*SIZE,
SIZE-1,
SIZE-1
);


}



function draw(){


ctx.clearRect(
0,
0,
canvas.width,
canvas.height
);



for(let y=0;y<ROWS;y++){

for(let x=0;x<COLS;x++){


if(board[y][x]){


drawCell(
x,
y,
colors[board[y][x]]
);


}


}

}




piece.shape.forEach((row,y)=>{

row.forEach((cell,x)=>{


if(cell){


drawCell(
piece.x+x,
piece.y+y,
colors[piece.type]
);


}



});

});


}




function collision(dx,dy,newShape=piece.shape){


for(let y=0;y<newShape.length;y++){


for(let x=0;x<newShape[y].length;x++){


if(newShape[y][x]){


let nx=piece.x+x+dx;

let ny=piece.y+y+dy;



if(

nx<0 ||

nx>=COLS ||

ny>=ROWS ||

(board[ny] && board[ny][nx])

)

return true;


}

}

}


return false;

}



function merge(){


piece.shape.forEach((row,y)=>{


row.forEach((cell,x)=>{


if(cell){


if(piece.y+y<0){

gameOver=true;

}


else{


board[
piece.y+y
][
piece.x+x
]
=
piece.type;


}


}



});

});


}



function clearLines(){


let cleared=0;


for(let y=ROWS-1;y>=0;y--){


if(board[y].every(cell=>cell)){


board.splice(y,1);

board.unshift(
Array(COLS).fill(null)
);


cleared++;

y++;

}


}



if(cleared){


lines+=cleared;


score += cleared*100*level;


level =
Math.floor(lines/10)+1;


updateInfo();


}


}




function rotate(){


let rotated =
piece.shape[0].map(
(_,i)=>
piece.shape.map(row=>row[i]).reverse()
);



if(!collision(0,0,rotated)){


piece.shape=rotated;


}


}




function drop(){


if(paused || gameOver)
return;



if(!collision(0,1)){


piece.y++;


}

else{


merge();

clearLines();


piece=randomPiece();


}


}



function hardDrop(){


while(!collision(0,1)){

piece.y++;

score+=2;

}


drop();


updateInfo();


}




function move(dir){


if(!collision(dir,0)){


piece.x+=dir;


}


}



function updateInfo(){


document.getElementById("score").innerHTML=score;

document.getElementById("lines").innerHTML=lines;

document.getElementById("level").innerHTML=level;


}



document.addEventListener(
"keydown",
e=>{


if(e.key==="ArrowLeft")
move(-1);


if(e.key==="ArrowRight")
move(1);



if(e.key==="ArrowDown")
drop();



if(e.key==="ArrowUp")
rotate();



if(e.code==="Space")
hardDrop();



if(e.key.toLowerCase()==="p")
paused=!paused;



if(e.key==="Enter" && gameOver)
restartGame();



}
);



function restartGame(){


board=createBoard();


piece=randomPiece();


score=0;

lines=0;

level=1;


gameOver=false;

paused=false;


updateInfo();


}



let last=0;



function loop(time){


if(!gameOver){


if(time-last >
800-level*60){


drop();


last=time;


}



draw();


}

else{


ctx.fillStyle="white";

ctx.font="40px Arial";

ctx.fillText(
"GAME OVER",
45,
300
);


}



requestAnimationFrame(loop);


}



restartGame();

requestAnimationFrame(loop);