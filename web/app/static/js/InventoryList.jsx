import React from "react";
import { Link } from "react-router-dom";


export default class InventoryList extends React.Component {

    constructor (props) {
        super(props);

        this.fetchInventories = this.fetchInventories.bind(this);
        this.handleNextPage = this.handleNextPage.bind(this);
        this.handlePrevPage = this.handlePrevPage.bind(this);

        this.state = {
            loading: true,
            total: null,
            page: null,
            pages: null,
            perPage: null,
            inventories: []
        }
    }

    fetchInventories (page = 1) {
        //this.setState({ loading: true });
        const filter = this.props.foreign ? 'foreign' : this.props.own ? 'own': 'all';
        const url = `/api/queries/inventory?owner_id=${this.props.ownerId}&filter=${filter}&getAttrs=all&pageNum=${page}`;

        fetch(url).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch inventories.')
        }).then(results => {
            this.setState({
                loading: false,
                total: results.total,
                page: results.page,
                pages: results.pages,
                perPage: results.per_page,
                inventories: results.items
            })
        }).catch(error => {
            alert(error);
            this.setState({
                loading: false,
                total: null,
                page: null,
                pages: null,
                perPage: null,
                inventories: []
            })
        })
    }

    componentDidMount () {
        this.fetchInventories()
    }

    handleNextPage () {
        if (this.state.page >= this.state.pages)
            return;
        this.fetchInventories(this.state.page + 1)
    }

    handlePrevPage () {
        if (this.state.page <= 1)
            return;
        this.fetchInventories(this.state.page - 1)
    }

    render () {
        return (
            <div className={"outlined"}>
                <h3>Inventories {this.state.loading ? '' : '(' + this.state.total + ')'}</h3>
                {this.state.loading
                    ? 'Loading...'
                    : <div>
                        <div>
                            <button onClick={this.handlePrevPage}>&lt;</button>
                            <span>Page {this.state.page} of {this.state.pages}</span>
                            <button onClick={this.handleNextPage}>&gt;</button>
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    {this.props.ownerId
                                        ? <th>SKU</th>
                                        : <th>Owner</th>
                                    }
                                    <th>Active</th>
                                    <th>Fulfillable</th>
                                    {this.props.ownerId
                                        ? <th>Title</th>
                                        : <th></th>
                                    }
                                </tr>
                            </thead>
                            <tbody>
                            {this.state.inventories.map(inv => {
                                return (
                                    <tr key={inv.id}>
                                        <td>{inv.id}</td>
                                        {this.props.ownerId
                                            ? <td>{inv.listing.sku}</td>
                                            : <td>{inv.owner.name}</td>
                                        }
                                        <td>{inv.active}</td>
                                        <td>{inv.fulfillable}</td>
                                        {this.props.ownerId
                                            ? <td>{inv.listing.title}</td>
                                            : <td></td>
                                        }
                                    </tr>
                                )
                            })}
                            </tbody>
                        </table>
                    </div>
                }
            </div>
        )
    }
}
