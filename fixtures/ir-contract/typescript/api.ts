export async function listOrders() {
  return fetch("/orders");
}
