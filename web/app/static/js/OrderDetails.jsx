import React from "react";


export default class OrderDetails extends React.Component {

    constructor (props) {
        super(props);

        this.fetchOrder = this.fetchOrder.bind(this);

        this.state = {
            loading: true,
            order: {}
        }
    }

    fetchOrder () {
        this.setState({ loading: true });

        fetch(`/api/obj/order?id=${this.props.orderId}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch order.')
        }).then(results => {
            this.setState({
                loading: false,
                order: results.items[0]
            })
        }).catch(error => {
            alert(error);
            this.setState({
                loading: false,
                order: {}
            })
        })
    }

    componentDidMount () {
        this.fetchOrder();
    }

    render () {
        return (
            <div className={"outlined"}>
                <pre>{JSON.stringify(this.state.order, null, '  ')}</pre>
            </div>
        )
    }
}