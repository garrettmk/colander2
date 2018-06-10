import React from "react";


export default class ExtraDetails extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            loading: true,
            data: {}
        }
    }

    componentDidMount () {
        this.setState({
            loading: true
        });

        const objType = this.props.objType;
        const objId = this.props.objId;

        fetch(`/api/obj/${objType}?id=${objId}&getAttrs=extra`).then(response => {
            if (response.ok)
                return response.json()
            throw new Error('Could not fetch extra data.')
        }).then(results => {
            this.setState({
                loading: false,
                data: results.items[0].extra
            })
        }).catch(error => {
            alert(error);
            this.setState({
                loading: false,
                data: {}
            })
        })
    }

    render () {
        return (
            <div className={"outlined"}>
                {this.state.loading
                    ? <span>Loading...</span>
                    : this.state.data
                        ? <pre>{JSON.stringify(this.state.data, null, '  ')}</pre>
                        : <span>None</span>
                }
            </div>
        )
    }
}
