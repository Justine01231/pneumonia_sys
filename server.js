const express = require("express");
const session = require("express-session");
const bodyParser = require("body-parser");

const app = express();

app.use(bodyParser.json());
app.use(express.static("public"));

app.use(session({
  secret: "pneumo-secret",
  resave: false,
  saveUninitialized: false
}));

// demo user
const USERS = [{ username:"admin", password:"1234" }];

// ---------- LOGIN ----------
app.post("/login",(req,res)=>{
  const {username,password} = req.body;
  const user = USERS.find(u=>u.username===username && u.password===password);
  if(!user) return res.json({ok:false});
  req.session.user=username;
  res.json({ok:true});
});

// ---------- LOGOUT ----------
app.post("/logout",(req,res)=>{
  req.session.destroy(()=>res.json({ok:true}));
});

// ---------- SESSION CHECK ----------
app.get("/me",(req,res)=>{
  res.json({logged: !!req.session.user});
});

// ---------- AI ANALYZE ----------
app.post("/analyze",(req,res)=>{
  if(!req.session.user) return res.status(401).json({error:"login required"});
  const result = Math.random()>.5 ? "Pneumonia" : "Normal";
  res.json({result});
});

app.listen(3000,()=>console.log("http://localhost:3000"));
