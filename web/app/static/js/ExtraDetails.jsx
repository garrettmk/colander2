import React from "react";


export default function ExtraDetails (props) {
    return (
        <div className={"outlined"}>
            {props.loading
                ? <span>Loading...</span>
                : props.data
                    ? <pre>{JSON.stringify(props.data, null, '  ')}</pre>
                    : <span>None</span>
            }
        </div>
    )
}