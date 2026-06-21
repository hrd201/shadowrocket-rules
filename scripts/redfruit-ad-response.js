// Return a valid no-fill response for ByteDance/Pangle ad SDK requests.
const response = {
  request_id: "",
  status_code: 20001,
  reason: 112,
  desc: "No ad available"
};

$done({
  headers: {
    "Content-Type": "application/json; charset=utf-8"
  },
  body: JSON.stringify(response)
});
