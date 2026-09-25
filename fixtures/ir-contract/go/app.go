package orders

import "net/http"

func listOrders(w http.ResponseWriter, r *http.Request) {
	http.HandleFunc("/orders", listOrders)
}
