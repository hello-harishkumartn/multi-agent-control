export function Status({value}: {value: string}) {
  return <span className={`status ${value.replaceAll("_", "-")}`}><i/>{value.replaceAll("_", " ")}</span>;
}

