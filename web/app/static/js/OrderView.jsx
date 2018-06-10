import React from "react";
import OrderDetails from "./OrderDetails";


export default class OrderView extends React.Component {

    constructor (props) {
        super(props);
    }



    fetchItems (orderId) {
        this.setState({ loading: true });

        fetch(`/api/obj/orderitem?order_id=${orderId}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch order items.')
        }).then(results => {
            this.setState({
                loading: false,
                items: results.items
            })
        })
    }

    render () {
        const orderId = this.props.match.params.orderId;

        return (
            <div>
                <OrderDetails orderId={orderId}/>
            </div>
        )
    }
}