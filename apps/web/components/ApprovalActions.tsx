"use client";
import { useState } from "react";

export function ApprovalActions({id, status}: {id:string; status:string}) {
  const [value,setValue]=useState(status);
  async function decide(decision:"approved"|"rejected"){
    setValue("submitting");
    const response=await fetch(`${process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000"}/api/v1/approvals/${id}/decision`,{method:"POST",headers:{"content-type":"application/json","x-api-key":"local-dev-key"},body:JSON.stringify({decision,comment:"Decided in operations console"})});
    if(response.ok){setValue(decision);window.location.reload()}else setValue("error");
  }
  if(value!=="pending")return <span className="actionState">{value}</span>;
  return <div className="approvalActions"><button onClick={()=>decide("approved")}>Approve</button><button onClick={()=>decide("rejected")}>Reject</button></div>;
}

