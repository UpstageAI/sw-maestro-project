const express = require("express");
const receiptRouter = require("./routes/receipt");

const app = express();
app.use(express.json());

app.get("/", (req, res) => {
  res.json({ message: "스마트 가계부 API" });
});

app.use("/receipt", receiptRouter);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`서버가 ${PORT}번 포트에서 실행 중입니다.`);
});
